from pathlib import Path
from typing import List, Optional

import subprocess
import shlex
import re

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


def detect_isolated_cpus() -> List[int]:
    """
    Tente de détecter les CPUs isolés via /sys/devices/system/cpu/isolated.
    Si rien n'est isolé, on renvoie tous les CPUs en ligne sauf le CPU0 par défaut.
    """
    isolated_path = Path("/sys/devices/system/cpu/isolated")
    if isolated_path.exists():
        content = isolated_path.read_text().strip()
        if content:
            cpus: List[int] = []
            for part in content.split(","):
                part = part.strip()
                if "-" in part:
                    start, end = part.split("-", 1)
                    cpus.extend(range(int(start), int(end) + 1))
                else:
                    cpus.append(int(part))
            return sorted(set(cpus))

    # Fallback: tous les CPUs en ligne sauf 0
    online_path = Path("/sys/devices/system/cpu/online")
    cpus: List[int] = []
    if online_path.exists():
        content = online_path.read_text().strip()
        for part in content.split(","):
            part = part.strip()
            if "-" in part:
                start, end = part.split("-", 1)
                cpus.extend(range(int(start), int(end) + 1))
            else:
                cpus.append(int(part))
    else:
        # Dernier fallback : on suppose 0-3
        cpus = list(range(4))

    return [c for c in sorted(set(cpus)) if c != 0] or cpus


app = FastAPI(title="rtperfui")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    isolated_cpus = detect_isolated_cpus()
    return templates.TemplateResponse(
        "cyclictest.html",
        {
            "request": request,
            "isolated_cpus": isolated_cpus,
            # Valeurs par défaut "classiques"
            "default_duration_s": 60,
            "default_interval_us": 200,
            "default_priority": 90,
            "default_policy": "fifo",
        },
    )


def build_cyclictest_cmd(
    duration_s: int,
    interval_us: int,
    priority: int,
    policy: str,
    distance_us: Optional[int],
    cpu_list: Optional[List[int]],
) -> List[str]:
    cmd = ["cyclictest"]

    # Politique temps réel : on évite -f qui n'est pas supporté partout.
    # On ne force rien pour FIFO (comportement par défaut), on ne met -r
    # que si l'utilisateur choisit SCHED_RR.
    if policy.lower() == "rr":
        cmd.append("-r")

    cmd += [
        "-D",
        str(duration_s),
        "-i",
        str(interval_us),
        "-p",
        str(priority),
        "-m",  # mlockall
        "-q",  # quiet header
        "-h",
        "90",  # histogram up to 90 us par défaut
    ]

    if distance_us is not None and distance_us > 0:
        cmd += ["-d", str(distance_us)]

    if cpu_list:
        cpu_str = ",".join(str(c) for c in cpu_list)
        cmd += ["-a", cpu_str]

        # On utilise autant de threads (-t) que de CPUs testés,
        # ce qui permet d'avoir un thread par CPU.
        threads = len(cpu_list)
        if threads > 0:
            cmd += ["-t", str(threads)]

    return cmd


def parse_cyclictest_output(raw: str) -> dict:
    """
    Parse grossièrement la sortie standard de cyclictest.
    On extrait une série de valeurs Max (pire latence observée à cet instant)
    pour construire un graphe simple, plus min/avg/max globaux si trouvés.
    """
    latencies: List[int] = []
    lines = raw.splitlines()
    global_min: Optional[int] = None
    global_max: Optional[int] = None
    global_avg: Optional[float] = None

    # 1) Tentative de parsing du format "classique" avec Min/Avg/Max.
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Lignes typiques: "T: 0 (  3982) P:99 I:1000 C:  6000 Min:      0 Act:   3 Avg:   2 Max:  13"
        if "Max:" in line and "Min:" in line and "Avg:" in line:
            parts = line.replace(":", " ").split()
            try:
                max_idx = parts.index("Max") + 1
                max_val = int(parts[max_idx])
                latencies.append(max_val)

                min_idx = parts.index("Min") + 1
                min_val = int(parts[min_idx])
                avg_idx = parts.index("Avg") + 1
                avg_val = float(avg_idx and parts[avg_idx])

                global_min = min_val if global_min is None else min(global_min, min_val)
                global_max = max_val if global_max is None else max(global_max, max_val)
                global_avg = avg_val  # dernier avg lu
            except (ValueError, IndexError):
                continue

    # 2) Si on n'a rien trouvé, fallback sur le format "histogramme" Debian.
    if not latencies:
        histogram_latencies: List[int] = []
        histogram_buckets: List[int] = []
        # counts par thread: index 0 -> thread 0, etc.
        histogram_counts_per_thread: List[List[int]] = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            # Format attendu: "<bucket> <count_t0> <count_t1> ..."
            if not parts[0].isdigit():
                continue
            try:
                bucket = int(parts[0])
                counts = [int(p) for p in parts[1:] if p.isdigit()]
            except ValueError:
                continue

            if not counts:
                continue

            total = sum(counts)

            # Initialisation de la structure par thread
            if not histogram_counts_per_thread:
                histogram_counts_per_thread = [[] for _ in range(len(counts))]

            # On aligne sur le nombre de threads détectés au début
            n_threads = min(len(histogram_counts_per_thread), len(counts))
            histogram_buckets.append(bucket)
            for idx in range(n_threads):
                histogram_counts_per_thread[idx].append(counts[idx])

            # Pour la liste "latencies" simplifiée et les stats globales,
            # on ne prend que les buckets où au moins un thread a vu cette latence.
            if total > 0:
                histogram_latencies.append(bucket)

        if histogram_latencies:
            latencies = histogram_latencies
            global_min = min(histogram_latencies)
            global_max = max(histogram_latencies)
            global_avg = sum(histogram_latencies) / len(histogram_latencies)

        # On essaie aussi de lire la ligne "# Max Latencies: ..." pour info.
        for line in lines:
            if line.strip().startswith("# Max Latencies"):
                parts = line.strip().split()
                # "# Max Latencies: 00006 00005 ..."
                nums: List[int] = []
                for p in parts[3:]:
                    p_clean = p.strip()
                    if p_clean.isdigit():
                        nums.append(int(p_clean))
                if nums:
                    max_from_summary = max(nums)
                    global_max = max_from_summary if global_max is None else max(
                        global_max, max_from_summary
                    )
                break

    return {
        "latencies": latencies,
        "histogram": {
            "buckets": histogram_buckets if "histogram_buckets" in locals() else [],
            # tableau 2D: histogram_counts_per_thread[thread_index][bucket_index]
            "per_thread_counts": histogram_counts_per_thread
            if "histogram_counts_per_thread" in locals()
            else [],
        },
        "summary": {
            "min": global_min,
            "max": global_max,
            "avg": global_avg,
        },
        "raw": raw,
    }


def build_hwlatdetect_cmd(
    duration_s: int,
    window_us: int,
    width_us: int,
    threshold_us: int,
) -> List[str]:
    """
    Construit une commande hwlatdetect avec quelques paramètres de base.
    """
    cmd = [
        "hwlatdetect",
        "--duration={}".format(duration_s),
        "--window={}".format(window_us),
        "--width={}".format(width_us),
        "--threshold={}".format(threshold_us),
    ]
    return cmd


def parse_hwlatdetect_output(raw: str) -> dict:
    """
    Parsing simple de la sortie de hwlatdetect.
    On essaye d'extraire des couples inner/outer (us) et on prend le max
    comme "latence" par échantillon.
    """
    latencies: List[int] = []
    samples_recorded: Optional[int] = None
    samples_exceeding: Optional[int] = None
    max_latency_below_threshold: Optional[bool] = None

    # Exemple de lignes qu'on vise (approx.) :
    # sample 00000000, inner: 12us, outer: 15us
    pattern = re.compile(r"inner:\s*(\d+)\s*us.*outer:\s*(\d+)\s*us", re.IGNORECASE)

    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        # Récupération d'éventuels résumés
        if stripped.startswith("Samples recorded:"):
            try:
                samples_recorded = int(stripped.split(":")[1])
            except (ValueError, IndexError):
                pass
        elif stripped.startswith("Samples exceeding threshold:"):
            try:
                samples_exceeding = int(stripped.split(":")[1])
            except (ValueError, IndexError):
                pass
        elif stripped.startswith("Max Latency:"):
            if "Below threshold" in stripped:
                max_latency_below_threshold = True

        # Parsing des lignes de samples détaillés (inner/outer)
        m = pattern.search(stripped)
        if m:
            inner = int(m.group(1))
            outer = int(m.group(2))
            latencies.append(max(inner, outer))

    global_min: Optional[int] = None
    global_max: Optional[int] = None
    global_avg: Optional[float] = None

    if latencies:
        global_min = min(latencies)
        global_max = max(latencies)
        global_avg = sum(latencies) / len(latencies)

    return {
        "latencies": latencies,
        "summary": {
            "min": global_min,
            "max": global_max,
            "avg": global_avg,
            "samples_recorded": samples_recorded,
            "samples_exceeding": samples_exceeding,
            "max_below_threshold": max_latency_below_threshold,
        },
        "raw": raw,
    }


@app.post("/api/cyclictest/run")
async def run_cyclictest(
    duration_s: int = Form(60),
    interval_us: int = Form(200),
    priority: int = Form(90),
    policy: str = Form("fifo"),
    distance_us: Optional[int] = Form(200),
    cpus: Optional[str] = Form(None),
):
    cpu_list: Optional[List[int]] = None
    if cpus:
        try:
            cpu_list = [int(c.strip()) for c in cpus.split(",") if c.strip()]
        except ValueError:
            return JSONResponse(
                {"error": "Liste de CPUs invalide"}, status_code=400
            )
    else:
        cpu_list = detect_isolated_cpus()

    cmd_list = build_cyclictest_cmd(
        duration_s=duration_s,
        interval_us=interval_us,
        priority=priority,
        policy=policy,
        distance_us=distance_us,
        cpu_list=cpu_list,
    )

    try:
        completed = subprocess.run(
            cmd_list,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return JSONResponse(
            {
                "error": "cyclictest introuvable sur le système. Veuillez installer le paquet rt-tests.",
                "command": " ".join(shlex.quote(x) for x in cmd_list),
            },
            status_code=500,
        )

    cmd_str = " ".join(shlex.quote(x) for x in cmd_list)

    if completed.returncode != 0:
        return JSONResponse(
            {
                "error": "cyclictest a retourné un code d'erreur",
                "returncode": completed.returncode,
                "stderr": completed.stderr,
                "stdout": completed.stdout,
                "command": cmd_str,
            },
            status_code=500,
        )

    parsed = parse_cyclictest_output(completed.stdout)
    return JSONResponse(
        {
            "command": cmd_str,
            "latencies": parsed["latencies"],
            "histogram": parsed.get("histogram"),
            "cpus_used": cpu_list,
            "summary": parsed["summary"],
            "raw_output": parsed["raw"],
        }
    )


@app.get("/hwlatdetect", response_class=HTMLResponse)
async def hwlatdetect_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "hwlatdetect.html",
        {
            "request": request,
            # Valeurs par défaut raisonnables, ajustables
            "default_duration_s": 60,
            "default_window_us": 1000000,  # 1 s
            "default_width_us": 500000,  # 0,5 s
            "default_threshold_us": 10,
        },
    )


@app.post("/api/hwlatdetect/run")
async def run_hwlatdetect(
    duration_s: int = Form(60),
    window_us: int = Form(1_000_000),
    width_us: int = Form(500_000),
    threshold_us: int = Form(10),
):
    cmd_list = build_hwlatdetect_cmd(
        duration_s=duration_s,
        window_us=window_us,
        width_us=width_us,
        threshold_us=threshold_us,
    )

    try:
        completed = subprocess.run(
            cmd_list,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return JSONResponse(
            {
                "error": "hwlatdetect introuvable sur le système. Veuillez installer l'outil approprié (souvent dans rt-tests ou un paquet similaire).",
                "command": " ".join(shlex.quote(x) for x in cmd_list),
            },
            status_code=500,
        )

    cmd_str = " ".join(shlex.quote(x) for x in cmd_list)

    if completed.returncode != 0:
        return JSONResponse(
            {
                "error": "hwlatdetect a retourné un code d'erreur",
                "returncode": completed.returncode,
                "stderr": completed.stderr,
                "stdout": completed.stdout,
                "command": cmd_str,
            },
            status_code=500,
        )

    parsed = parse_hwlatdetect_output(completed.stdout)
    return JSONResponse(
        {
            "command": cmd_str,
            "latencies": parsed["latencies"],
            "summary": parsed["summary"],
            "raw_output": parsed["raw"],
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


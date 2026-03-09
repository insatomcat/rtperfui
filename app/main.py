from pathlib import Path
from typing import List, Optional

import subprocess
import shlex

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
    cpu_list: Optional[List[int]],
) -> List[str]:
    cmd = ["cyclictest"]

    # Politique temps réel
    if policy.lower() == "fifo":
        cmd.append("-f")
    elif policy.lower() == "rr":
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

    if cpu_list:
        cpu_str = ",".join(str(c) for c in cpu_list)
        cmd += ["-a", cpu_str]

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

    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Lignes typiques: "T: 0 (  3982) P:99 I:1000 C:  6000 Min:      0 Act:   3 Avg:   2 Max:  13"
        if "Max:" in line:
            parts = line.replace(":", " ").split()
            try:
                max_idx = parts.index("Max") + 1
                max_val = int(parts[max_idx])
                latencies.append(max_val)

                min_idx = parts.index("Min") + 1
                min_val = int(parts[min_idx])
                avg_idx = parts.index("Avg") + 1
                avg_val = float(parts[avg_idx])

                global_min = min_val if global_min is None else min(global_min, min_val)
                global_max = max_val if global_max is None else max(global_max, max_val)
                global_avg = avg_val  # dernier avg lu
            except (ValueError, IndexError):
                continue

    return {
        "latencies": latencies,
        "summary": {
            "min": global_min,
            "max": global_max,
            "avg": global_avg,
        },
        "raw": raw,
    }


@app.post("/api/cyclictest/run")
async def run_cyclictest(
    duration_s: int = Form(60),
    interval_us: int = Form(200),
    priority: int = Form(90),
    policy: str = Form("fifo"),
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

    if completed.returncode != 0:
        return JSONResponse(
            {
                "error": "cyclictest a retourné un code d'erreur",
                "returncode": completed.returncode,
                "stderr": completed.stderr,
            },
            status_code=500,
        )

    parsed = parse_cyclictest_output(completed.stdout)
    return JSONResponse(
        {
            "command": " ".join(shlex.quote(x) for x in cmd_list),
            "latencies": parsed["latencies"],
            "summary": parsed["summary"],
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


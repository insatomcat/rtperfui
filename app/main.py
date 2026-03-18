from pathlib import Path
from typing import List, Optional, Dict, Any

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

SUPPORTED_LANGS = ("fr", "en")


TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "fr": {
        "subtitle": "Interface de test de performances temps réel",
        "tab_cyclictest": "cyclictest",
        "tab_hwlatdetect": "hwlatdetect",
        "tab_systemcheck": "systemcheck",
        "lang_fr": "FR",
        "lang_en": "EN",
        "cyclictest_title": "Lancer un test cyclictest",
        "cyclictest_duration": "Durée (secondes)",
        "cyclictest_duration_help": "Temps total d'exécution du test.",
        "cyclictest_interval": "Intervalle (µs)",
        "cyclictest_interval_help": "Période de réveil de la tâche temps réel.",
        "cyclictest_priority": "Priorité RT (SCHED_FIFO)",
        "cyclictest_priority_help": "Priorité temps réel (1-99).",
        "cyclictest_policy": "Politique temps réel",
        "cyclictest_policy_help": "Politique d'ordonnancement temps réel.",
        "cyclictest_cpus": "Affinité CPU",
        "cyclictest_cpus_placeholder": "ex: 2,3 ou 1-3 (laisse vide pour CPUs isolés détectés)",
        "cyclictest_cpus_help_prefix": "CPUs isolés détectés par défaut :",
        "cyclictest_cpus_help_fallback": "aucun CPU isolé détecté, fallback sur tous les CPUs hors CPU0.",
        "cyclictest_distance": "Distance (-d, µs)",
        "cyclictest_distance_help": "Option -d de cyclictest. Laisser 0 pour ne pas la passer.",
        "cyclictest_run": "Lancer le test",
        "cyclictest_running": "Test en cours, merci de patienter…",
        "cyclictest_done": "Test terminé.",
        "cyclictest_parse_error": "Test terminé mais aucune latence n'a été parsée, vérifiez la sortie de cyclictest.",
        "cyclictest_error": "Erreur lors de l'exécution de cyclictest",
        "cyclictest_hist_title": "Histogramme des latences (échelle log)",
        "cyclictest_details_title": "Détails commande / sortie cyclictest",
        "details_command": "Commande :",
        "details_output": "Sortie (stdout/stderr) :",
        "hwlat_title": "Lancer un test hwlatdetect",
        "hwlat_duration": "Durée (secondes)",
        "hwlat_duration_help": "Durée totale de la campagne de détection.",
        "hwlat_window": "Fenêtre (µs)",
        "hwlat_window_help": "Taille de la fenêtre d'observation.",
        "hwlat_width": "Largeur (µs)",
        "hwlat_width_help": "Largeur de l'intervalle de mesure dans la fenêtre.",
        "hwlat_threshold": "Seuil (µs)",
        "hwlat_threshold_help": "Seuil de latence au-delà duquel un outlier est signalé.",
        "hwlat_run": "Lancer le test",
        "hwlat_running": "Test hwlatdetect en cours, merci de patienter…",
        "hwlat_done": "Test hwlatdetect terminé.",
        "hwlat_chart_title": "Latences observées (hwlatdetect)",
        "hwlat_details_title": "Détails commande / sortie hwlatdetect",
        "hwlat_error": "Erreur lors de l'exécution de hwlatdetect",
        "hwlat_parse_warn": "Test terminé mais aucune latence n'a été parsée, vérifiez la sortie de hwlatdetect.",
        "hwlat_no_samples_status": "Test hwlatdetect terminé, aucune latence mesurée au-dessus du seuil.",
        "hwlat_no_samples_summary_prefix": "échantillons totaux:",
        "hwlat_no_samples_summary_middle": "· au-dessus du seuil:",
        "systemcheck_title": "Vérifications système temps réel",
        "systemcheck_intro": (
            "Un clic lance une série de checks sur la configuration de la machine hôte "
            "(noyau, boot, CPU, hugepages, PTP, etc.) et produit un rapport synthétique."
        ),
        "systemcheck_run": "Lancer les checks",
        "systemcheck_running": "Checks en cours…",
        "systemcheck_done": "Checks terminés",
        "systemcheck_report": "Rapport",
        "systemcheck_error": "Erreur lors des vérifications système.",
        "status_ok": "OK",
        "status_warn": "ATTENTION",
        "status_fail": "ÉCHEC",
        "status_info": "INFO",
        "summary_line": "min: {min} µs · avg: {avg} µs · max: {max} µs",
        "summary_line_per_cpu": "{label} — min: {min} µs · avg: {avg} µs · max: {max} µs · samples: {samples}",
    },
    "en": {
        "subtitle": "Real-time performance test interface",
        "tab_cyclictest": "cyclictest",
        "tab_hwlatdetect": "hwlatdetect",
        "tab_systemcheck": "systemcheck",
        "lang_fr": "FR",
        "lang_en": "EN",
        "cyclictest_title": "Run a cyclictest",
        "cyclictest_duration": "Duration (seconds)",
        "cyclictest_duration_help": "Total test duration.",
        "cyclictest_interval": "Interval (µs)",
        "cyclictest_interval_help": "Wakeup period of the real-time task.",
        "cyclictest_priority": "RT priority (SCHED_FIFO)",
        "cyclictest_priority_help": "Real-time priority (1-99).",
        "cyclictest_policy": "Real-time policy",
        "cyclictest_policy_help": "Real-time scheduling policy.",
        "cyclictest_cpus": "CPU affinity",
        "cyclictest_cpus_placeholder": "e.g. 2,3 or 1-3 (leave empty for detected isolated CPUs)",
        "cyclictest_cpus_help_prefix": "Default isolated CPUs:",
        "cyclictest_cpus_help_fallback": "no isolated CPU detected, falling back to all CPUs except CPU0.",
        "cyclictest_distance": "Distance (-d, µs)",
        "cyclictest_distance_help": "cyclictest -d option. Leave 0 to skip it.",
        "cyclictest_run": "Run test",
        "cyclictest_running": "Test running, please wait…",
        "cyclictest_done": "Test finished.",
        "cyclictest_parse_error": "Test finished but no latency could be parsed, please check cyclictest output.",
        "cyclictest_error": "Error while executing cyclictest",
        "cyclictest_hist_title": "Latency histogram (log scale)",
        "cyclictest_details_title": "cyclictest command / output details",
        "details_command": "Command:",
        "details_output": "Output (stdout/stderr):",
        "hwlat_title": "Run a hwlatdetect test",
        "hwlat_duration": "Duration (seconds)",
        "hwlat_duration_help": "Total duration of the detection campaign.",
        "hwlat_window": "Window (µs)",
        "hwlat_window_help": "Size of the observation window.",
        "hwlat_width": "Width (µs)",
        "hwlat_width_help": "Measurement interval width within the window.",
        "hwlat_threshold": "Threshold (µs)",
        "hwlat_threshold_help": "Latency threshold above which an outlier is reported.",
        "hwlat_run": "Run test",
        "hwlat_running": "hwlatdetect test running, please wait…",
        "hwlat_done": "hwlatdetect test finished.",
        "hwlat_chart_title": "Observed latencies (hwlatdetect)",
        "hwlat_details_title": "hwlatdetect command / output details",
        "hwlat_error": "Error while executing hwlatdetect",
        "hwlat_parse_warn": "Test finished but no latency could be parsed, please check hwlatdetect output.",
        "hwlat_no_samples_status": "hwlatdetect test finished, no latency measured above threshold.",
        "hwlat_no_samples_summary_prefix": "total samples:",
        "hwlat_no_samples_summary_middle": "· above threshold:",
        "systemcheck_title": "Real-time system checks",
        "systemcheck_intro": (
            "One click runs a series of checks on the host configuration "
            "(kernel, boot, CPU, hugepages, PTP, etc.) and produces a synthetic report."
        ),
        "systemcheck_run": "Run checks",
        "systemcheck_running": "Running checks…",
        "systemcheck_done": "Checks completed",
        "systemcheck_report": "Report",
        "systemcheck_error": "Error while running system checks.",
        "status_ok": "OK",
        "status_warn": "WARNING",
        "status_fail": "FAIL",
        "status_info": "INFO",
        "summary_line": "min: {min} µs · avg: {avg} µs · max: {max} µs",
        "summary_line_per_cpu": "{label} — min: {min} µs · avg: {avg} µs · max: {max} µs · samples: {samples}",
    },
}


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


def get_lang_from_request(request: Request) -> str:
    # 1) Query parameter override
    qp = request.query_params.get("lang")
    if qp in SUPPORTED_LANGS:
        return qp

    # 2) Accept-Language header
    header = request.headers.get("accept-language", "").lower()
    if header.startswith("fr") or " fr" in header:
        return "fr"

    # 3) Default
    return "en"


def t(lang: str, key: str) -> str:
    lang_dict = TRANSLATIONS.get(lang) or TRANSLATIONS["en"]
    return lang_dict.get(key, TRANSLATIONS["en"].get(key, key))


# Inject translation helper globally into Jinja
templates.env.globals["t"] = t


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    lang = get_lang_from_request(request)
    isolated_cpus = detect_isolated_cpus()
    return templates.TemplateResponse(
        "cyclictest.html",
        {
            "request": request,
            "lang": lang,
            "active_tab": "cyclictest",
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


def parse_cpu_list(expr: str) -> List[int]:
    """
    Parse une expression CPU du type:
    - "1,2,3"
    - "1-3"
    - "1-3,8,10-12"
    """
    cpus: List[int] = []
    for part in expr.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_s, end_s = part.split("-", 1)
            start_s = start_s.strip()
            end_s = end_s.strip()
            if not start_s.isdigit() or not end_s.isdigit():
                raise ValueError("invalid range")
            start = int(start_s)
            end = int(end_s)
            if end < start:
                raise ValueError("invalid range order")
            cpus.extend(range(start, end + 1))
        else:
            if not part.isdigit():
                raise ValueError("invalid cpu id")
            cpus.append(int(part))
    # unique + tri
    return sorted(set(cpus))


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
        max_latencies_from_summary: List[int] = []
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
                max_latencies_from_summary = nums
                if nums:
                    max_from_summary = max(nums)
                    global_max = max_from_summary if global_max is None else max(
                        global_max, max_from_summary
                    )
                break

    # 3) Statistiques par thread/CPU sur la base de l'histogramme
    summary_per_thread: List[dict] = []
    if "histogram_buckets" in locals() and "histogram_counts_per_thread" in locals():
        for idx, counts in enumerate(histogram_counts_per_thread):
            if not counts:
                summary_per_thread.append(
                    {"thread_index": idx, "min": None, "max": None, "avg": None, "total_samples": 0}
                )
                continue

            total_samples = sum(counts)
            if total_samples == 0:
                summary_per_thread.append(
                    {"thread_index": idx, "min": None, "max": None, "avg": None, "total_samples": 0}
                )
                continue

            per_min: Optional[int] = None
            per_max: Optional[int] = None
            acc = 0
            for bucket, count in zip(histogram_buckets, counts):
                if count <= 0:
                    continue
                if per_min is None:
                    per_min = bucket
                per_max = bucket
                acc += bucket * count

            # Ajuste le max avec la ligne "# Max Latencies" si disponible
            if max_latencies_from_summary and idx < len(max_latencies_from_summary):
                max_from_summary = max_latencies_from_summary[idx]
                if per_max is None or max_from_summary > per_max:
                    per_max = max_from_summary

            per_avg: Optional[float] = None
            if total_samples > 0 and acc > 0:
                per_avg = acc / total_samples

            summary_per_thread.append(
                {
                    "thread_index": idx,
                    "min": per_min,
                    "max": per_max,
                    "avg": per_avg,
                    "total_samples": total_samples,
                }
            )

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
        "summary_per_thread": summary_per_thread,
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
    events: List[Dict[str, Any]] = []
    samples_recorded: Optional[int] = None
    samples_exceeding: Optional[int] = None
    max_latency_below_threshold: Optional[bool] = None

    # Exemple de lignes qu'on vise (approx.) :
    # sample 00000000, inner: 12us, outer: 15us
    # ts: 1773668004.982201597, inner:0, outer:13, cpu:5
    pattern = re.compile(r"inner:\s*(\d+)(?:\s*us)?\s*,?\s*outer:\s*(\d+)(?:\s*us)?", re.IGNORECASE)
    ts_cpu_pattern = re.compile(
        r"ts:\s*([0-9]+\.[0-9]+)\s*,\s*inner:\s*(\d+)(?:\s*us)?\s*,\s*outer:\s*(\d+)(?:\s*us)?\s*,\s*cpu:\s*(\d+)",
        re.IGNORECASE,
    )

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

        # Parsing des lignes de samples détaillés (inner/outer + éventuellement ts/cpu)
        m_ts = ts_cpu_pattern.search(stripped)
        if m_ts:
            ts = float(m_ts.group(1))
            inner = int(m_ts.group(2))
            outer = int(m_ts.group(3))
            cpu = int(m_ts.group(4))
            latency = max(inner, outer)
            latencies.append(latency)
            events.append(
                {
                    "ts": ts,
                    "inner": inner,
                    "outer": outer,
                    "cpu": cpu,
                    "latency": latency,
                }
            )
            continue

        # Fallback: lignes sans ts/cpu explicites
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
        "events": events,
        "raw": raw,
    }


def _run_cmd(cmd: List[str]) -> Dict[str, Any]:
    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=3,
        )
        return {
            "returncode": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


def run_system_checks() -> List[Dict[str, Any]]:
    checks: List[Dict[str, Any]] = []

    # tuned profile (host-level tuning daemon)
    tuned_profile: Optional[str] = None
    # 1) Try from well-known files (works in container if /run or /etc tuned dirs are bind-mounted)
    for p in (Path("/run/tuned/active_profile"), Path("/etc/tuned/active_profile")):
        if p.exists():
            try:
                tuned_profile = p.read_text().strip()
                break
            except OSError:
                continue

    if tuned_profile:
        if "realtime" in tuned_profile or "seapath" in tuned_profile:
            status = "ok"
            msg = f"Profil tuned actif: {tuned_profile}"
        else:
            status = "warn"
            msg = f"Profil tuned actif non temps réel ou inconnu: {tuned_profile}"
    else:
        # 2) Fallback: tuned-adm (bare-metal host case). Missing tool is informational, not an error.
        tuned_info = _run_cmd(["tuned-adm", "active"])
        if "error" in tuned_info or tuned_info.get("returncode", 1) != 0:
            status = "info"
            msg = "Impossible de déterminer le profil tuned (ni fichiers active_profile, ni tuned-adm disponibles)."
        else:
            out = tuned_info.get("stdout", "")
            if "Current active profile" in out and ("realtime" in out or "seapath" in out):
                status = "ok"
                msg = out
            else:
                status = "warn"
                msg = f"Profil tuned actif non temps réel ou inconnu: {out}"
    checks.append(
        {
            "id": "tuned",
            "name": "Profil tuned",
            "status": status,
            "details": msg,
        }
    )

    # CPU isolation
    isolated = detect_isolated_cpus()
    if isolated:
        status = "ok"
        msg = f"CPUs isolés détectés: {', '.join(map(str, isolated))}"
    else:
        status = "warn"
        msg = "Aucun CPU isolé détecté (ni dans /sys/devices/system/cpu/isolated, ni via fallback)."
    checks.append(
        {
            "id": "cpu_isolation",
            "name": "Isolation CPU",
            "status": status,
            "details": msg,
        }
    )

    # Hyperthreading
    smt_path = Path("/sys/devices/system/cpu/smt/active")
    if smt_path.exists():
        try:
            active = smt_path.read_text().strip()
            if active == "0":
                status = "ok"
                msg = "Hyperthreading désactivé (smt/active=0)."
            else:
                status = "warn"
                msg = "Hyperthreading activé (smt/active!=0) – peut être défavorable au temps réel."
        except OSError as exc:  # noqa: PERF203
            status = "warn"
            msg = f"Impossible de lire smt/active: {exc}"
    else:
        status = "info"
        msg = "Pas d'information SMT explicite (smt/active absent)."
    checks.append(
        {
            "id": "hyperthreading",
            "name": "Hyperthreading / SMT",
            "status": status,
            "details": msg,
        }
    )

    # PREEMPT_RT
    uname_info = _run_cmd(["uname", "-v"])
    if "error" in uname_info:
        status = "warn"
        msg = "Impossible de récupérer uname -v."
    else:
        ver = uname_info.get("stdout", "")
        if "PREEMPT_RT" in ver:
            status = "ok"
            msg = f"Noyau PREEMPT_RT détecté ({ver})."
        elif "PREEMPT" in ver:
            status = "warn"
            msg = f"Noyau préemptible sans RT complet ({ver})."
        else:
            status = "warn"
            msg = f"Noyau probablement non temps réel ({ver})."
    checks.append(
        {
            "id": "preempt_rt",
            "name": "Préemption noyau (PREEMPT_RT)",
            "status": status,
            "details": msg,
        }
    )

    # CMDLINE
    cmdline_path = Path("/proc/cmdline")
    problematic_flags: List[str] = []
    rt_friendly_flags: List[str] = []
    if cmdline_path.exists():
        cmd = cmdline_path.read_text().strip()
        if "intel_pstate=disable" in cmd or "intel_pstate=passive" in cmd:
            rt_friendly_flags.append("intel_pstate=disable/passive")
        if "processor.max_cstate=1" in cmd or "idle=poll" in cmd:
            rt_friendly_flags.append("C-states limités (processor.max_cstate / idle=poll)")
        if "nohz_full" in cmd:
            rt_friendly_flags.append("nohz_full configuré")
        if "rcu_nocbs" in cmd:
            rt_friendly_flags.append("rcu_nocbs configuré")

        if "intel_idle.max_cstate=0" not in cmd and "processor.max_cstate" not in cmd:
            problematic_flags.append("Pas de limitation explicite des C-states (intel_idle/processor.max_cstate).")
        if "lapic_timer_c2_ok" in cmd:
            problematic_flags.append("lapic_timer_c2_ok peut introduire de la gigue sur certains matériels.")

        msg_parts = [f"cmdline: {cmd}"]
        if rt_friendly_flags:
            msg_parts.append("Paramètres favorables RT: " + "; ".join(rt_friendly_flags))
        if problematic_flags:
            msg_parts.append("Points d'attention: " + "; ".join(problematic_flags))

        if problematic_flags:
            status = "warn"
        else:
            status = "ok"
        msg = "\n".join(msg_parts)
    else:
        status = "warn"
        msg = "/proc/cmdline introuvable."
    checks.append(
        {
            "id": "cmdline",
            "name": "Paramètres de boot (cmdline)",
            "status": status,
            "details": msg,
        }
    )

    # sysctl
    sched_rt_runtime = Path("/proc/sys/kernel/sched_rt_runtime_us")
    sched_rt_period = Path("/proc/sys/kernel/sched_rt_period_us")
    sysctl_msgs: List[str] = []
    status = "ok"
    if sched_rt_runtime.exists() and sched_rt_period.exists():
        try:
            rt_runtime = int(sched_rt_runtime.read_text().strip())
            rt_period = int(sched_rt_period.read_text().strip())
            sysctl_msgs.append(f"sched_rt_runtime_us={rt_runtime}, sched_rt_period_us={rt_period}")
            if rt_runtime >= 0 and rt_runtime < rt_period:
                status = "warn"
                sysctl_msgs.append("Les tâches RT ne peuvent pas utiliser 100% du CPU (runtime < period).")
        except ValueError:
            status = "warn"
            sysctl_msgs.append("Valeurs sched_rt_* non numériques.")
    else:
        status = "warn"
        sysctl_msgs.append("Paramètres sched_rt_* introuvables.")
    checks.append(
        {
            "id": "sysctl_rt",
            "name": "Paramètres RT (sysctl)",
            "status": status,
            "details": "\n".join(sysctl_msgs),
        }
    )

    # ACPI
    acpi_dir = Path("/sys/firmware/acpi")
    acpi_ok = acpi_dir.exists()
    if not acpi_ok:
        status = "info"
        msg = "ACPI désactivé ou non présent (peut être souhaité pour le RT)."
    else:
        status = "info"
        msg = "ACPI actif; certaines configurations ACPI peuvent impacter la latence, à vérifier."
    checks.append(
        {
            "id": "acpi",
            "name": "ACPI",
            "status": status,
            "details": msg,
        }
    )

    # Hugepages / THP
    huge_nr = Path("/proc/sys/vm/nr_hugepages")
    thp = Path("/sys/kernel/mm/transparent_hugepage/enabled")
    hp_msgs: List[str] = []
    if huge_nr.exists():
        try:
            nr = int(huge_nr.read_text().strip())
            hp_msgs.append(f"nr_hugepages={nr}")
        except ValueError:
            hp_msgs.append("nr_hugepages non numérique.")
    if thp.exists():
        val = thp.read_text().strip()
        hp_msgs.append(f"transparent_hugepage.enabled={val}")
        if "[never]" not in val:
            status = "warn"
            hp_msgs.append("THP n'est pas complètement désactivé ([never] recommandé pour RT).")
        else:
            status = "ok"
    else:
        status = "info"
        hp_msgs.append("Transparent Huge Pages (THP) non détecté.")
    checks.append(
        {
            "id": "hugepages",
            "name": "Hugepages / Transparent Huge Pages",
            "status": status,
            "details": "\n".join(hp_msgs),
        }
    )

    # IRQ affinity (vue générale)
    irq_dir = Path("/proc/irq")
    irq_msg = "Affinité IRQ non inspectée (réduction pour la première version du check)."
    if irq_dir.exists():
        irq_msg = (
            "Les fichiers /proc/irq/*/smp_affinity décrivent l'affinité des IRQ. "
            "Une configuration affinée vers les CPUs non-RT est recommandée."
        )
    checks.append(
        {
            "id": "irq_affinity",
            "name": "Affinité IRQ",
            "status": "info",
            "details": irq_msg,
        }
    )

    # PTP / synchronisation temps
    ptp_dir = Path("/sys/class/ptp")
    if ptp_dir.exists() and any(ptp_dir.iterdir()):
        status = "info"
        msg = "Horloge(s) PTP détectée(s) dans /sys/class/ptp. Vérifier ptp4l/phc2sys pour la synchronisation."
    else:
        status = "info"
        msg = "Aucune horloge PTP détectée dans /sys/class/ptp."
    checks.append(
        {
            "id": "ptp",
            "name": "Synchronisation PTP",
            "status": status,
            "details": msg,
        }
    )

    return checks


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
            cpu_list = parse_cpu_list(cpus)
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
            "summary_per_thread": parsed.get("summary_per_thread"),
            "raw_output": parsed["raw"],
        }
    )


@app.get("/hwlatdetect", response_class=HTMLResponse)
async def hwlatdetect_page(request: Request) -> HTMLResponse:
    lang = get_lang_from_request(request)
    return templates.TemplateResponse(
        "hwlatdetect.html",
        {
            "request": request,
            "lang": lang,
            "active_tab": "hwlatdetect",
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

    parsed = parse_hwlatdetect_output(completed.stdout)
    return JSONResponse(
        {
            "command": cmd_str,
            "returncode": completed.returncode,
            "latencies": parsed["latencies"],
            "summary": parsed["summary"],
            "events": parsed.get("events"),
            "raw_output": parsed["raw"],
        }
    )


@app.get("/systemcheck", response_class=HTMLResponse)
async def systemcheck_page(request: Request) -> HTMLResponse:
    lang = get_lang_from_request(request)
    return templates.TemplateResponse(
        "systemcheck.html",
        {
            "request": request,
            "lang": lang,
            "active_tab": "systemcheck",
        },
    )


@app.get("/api/systemcheck/run")
async def systemcheck_run():
    checks = run_system_checks()
    return JSONResponse({"checks": checks})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


from pathlib import Path
from typing import List, Optional, Dict, Any

import subprocess
import shlex
import re
import bz2
import xml.etree.ElementTree as ET

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
        "tab_seapath": "seapath",
        "seapath_title": "Configuration Seapath",
        "seapath_intro": (
            "Vérifie la configuration Seapath de la machine hôte : mode cluster/standalone, "
            "configuration RT (tuned, cmdline, sysctl), hugepages et affectation CPU des VM."
        ),
        "seapath_run": "Analyser",
        "seapath_running": "Analyse en cours…",
        "seapath_done": "Analyse terminée",
        "seapath_error": "Erreur lors de l'analyse Seapath",
        "seapath_cluster_status": "Statut cluster",
        "seapath_rt_config": "Configuration RT",
        "seapath_hugepages": "Hugepages",
        "seapath_cpu_map": "Carte d'affectation CPU",
        "seapath_vm_details": "Détails des VM",
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
        "tab_seapath": "seapath",
        "seapath_title": "Seapath Configuration",
        "seapath_intro": (
            "Checks the Seapath configuration of the host machine: cluster/standalone mode, "
            "RT configuration (tuned, cmdline, sysctl), hugepages and VM CPU assignment."
        ),
        "seapath_run": "Analyze",
        "seapath_running": "Analyzing…",
        "seapath_done": "Analysis complete",
        "seapath_error": "Error during Seapath analysis",
        "seapath_cluster_status": "Cluster status",
        "seapath_rt_config": "RT Configuration",
        "seapath_hugepages": "Hugepages",
        "seapath_cpu_map": "CPU Assignment Map",
        "seapath_vm_details": "VM Details",
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


def _run_cmd(cmd: List[str], timeout: int = 3) -> Dict[str, Any]:
    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
        return {
            "returncode": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


def _run_host_cmd(cmd: List[str], timeout: int = 15) -> Dict[str, Any]:
    """Run a command directly; if not found, retry via nsenter into PID-1 namespaces."""
    try:
        completed = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=timeout)
        return {"returncode": completed.returncode, "stdout": completed.stdout.strip(), "stderr": completed.stderr.strip()}
    except FileNotFoundError:
        pass
    except Exception as exc:
        return {"error": str(exc)}
    nsenter = ["nsenter", "--target", "1", "--mount", "--uts", "--ipc", "--net", "--pid", "--"] + cmd
    try:
        completed = subprocess.run(nsenter, capture_output=True, text=True, check=False, timeout=timeout)
        return {"returncode": completed.returncode, "stdout": completed.stdout.strip(), "stderr": completed.stderr.strip()}
    except Exception as exc:
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


# ---------------------------------------------------------------------------
# Seapath helpers
# ---------------------------------------------------------------------------

def _parse_cpuset(s: str) -> List[int]:
    cpus: List[int] = []
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            try:
                cpus.extend(range(int(a.strip()), int(b.strip()) + 1))
            except ValueError:
                pass
        elif part.isdigit():
            cpus.append(int(part))
    return sorted(set(cpus))


def _get_all_cpus() -> List[int]:
    online_path = Path("/sys/devices/system/cpu/online")
    cpus: List[int] = []
    if online_path.exists():
        content = online_path.read_text().strip()
        for part in content.split(","):
            part = part.strip()
            if "-" in part:
                a, b = part.split("-", 1)
                try:
                    cpus.extend(range(int(a), int(b) + 1))
                except ValueError:
                    pass
            elif part.isdigit():
                cpus.append(int(part))
    if not cpus:
        try:
            content = Path("/proc/cpuinfo").read_text()
            for m in re.finditer(r"^processor\s*:\s*(\d+)", content, re.MULTILINE):
                cpus.append(int(m.group(1)))
        except OSError:
            pass
    return sorted(set(cpus))


def _get_cpu_topology(cpus: List[int]) -> Dict[int, Dict[str, Any]]:
    """Read CPU topology from sysfs for HT/core grouping."""
    topo: Dict[int, Dict[str, Any]] = {}
    for cpu in cpus:
        base = Path(f"/sys/devices/system/cpu/cpu{cpu}/topology")
        core_id: Optional[int] = None
        package_id: Optional[int] = None
        siblings: List[int] = [cpu]

        try:
            p = base / "core_id"
            if p.exists():
                core_id = int(p.read_text().strip())
        except (OSError, ValueError):
            pass
        try:
            p = base / "physical_package_id"
            if p.exists():
                package_id = int(p.read_text().strip())
        except (OSError, ValueError):
            pass
        try:
            sib = base / "thread_siblings_list"
            if sib.exists():
                siblings = _parse_cpuset(sib.read_text().strip()) or [cpu]
        except OSError:
            pass

        topo[cpu] = {
            "cpu": cpu,
            "core_id": core_id,
            "package_id": package_id,
            "thread_siblings": siblings,
        }

    return topo


CIB_PATHS = [
    # Runtime CIB locations (preferred: includes <status>)
    Path("/run/pacemaker/cib/cib.xml"),
    Path("/run/pcmk/cib/cib.xml"),
    # Persistent/on-disk CIB (can be config-only on some setups)
    Path("/var/lib/pacemaker/cib/cib.xml"),
    Path("/var/lib/heartbeat/crm/cib.xml"),
]


def _xml_local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def _xml_find_first_by_local_name(parent: Any, name: str) -> Optional[Any]:
    if parent is None:
        return None
    for elt in parent.iter():
        if _xml_local_name(elt.tag) == name:
            return elt
    return None


def _xml_find_all_by_local_name(parent: Any, name: str) -> List[Any]:
    if parent is None:
        return []
    return [elt for elt in parent.iter() if _xml_local_name(elt.tag) == name]



def _safe_call_id(op: Any) -> int:
    try:
        v = int(op.get("call-id", -1))
        return v if v >= 0 else -1
    except (ValueError, TypeError):
        return -1


def _cib_ops_for_resource(node_state_elt: Any, resource_id: str) -> List[Any]:
    """Collect all operation elements for resource_id under a node_state.

    Uses iter() at every level to be resilient to any intermediate wrapper elements,
    and covers both pacemaker 2.x (lrm_rsc_op) and 3.x (op_history) naming.
    """
    ops: List[Any] = []
    op_tags = {"lrm_rsc_op", "op_history"}
    rsc_tags = {"lrm_resource", "resource_history"}

    for rsc_elt in node_state_elt.iter():
        tag = _xml_local_name(rsc_elt.tag)
        if tag not in rsc_tags:
            continue
        # Pacemaker versions may encode resource identity with different attrs.
        rsc_ids = {
            rsc_elt.get("id"),
            rsc_elt.get("resource"),
            rsc_elt.get("rsc-id"),
        }
        if resource_id in rsc_ids:
            for op_elt in rsc_elt.iter():
                if _xml_local_name(op_elt.tag) in op_tags:
                    ops.append(op_elt)

    return ops


def _cib_resource_status(status_elt: Any, resource_id: str) -> Dict[str, Any]:
    """Return {"host": str|None, "node_summaries": [...], "_debug_children": [...]}."""
    if status_elt is None:
        return {"host": None, "node_summaries": []}

    best_host: Optional[str] = None
    node_summaries: List[Dict] = []
    total_ops = 0

    # Debug: record all direct child tags of status and node_state for diagnosis
    status_child_tags = sorted({_xml_local_name(c.tag) for c in status_elt})

    for ns in _xml_find_all_by_local_name(status_elt, "node_state"):
        node_name = ns.get("uname") or ns.get("id", "?")
        ns_child_tags = sorted({_xml_local_name(c.tag) for c in ns})
        ops = _cib_ops_for_resource(ns, resource_id)
        total_ops += len(ops)
        has_shutdown = False
        for nvpair in _xml_find_all_by_local_name(ns, "nvpair"):
            if nvpair.get("name") == "shutdown" and nvpair.get("value"):
                has_shutdown = True
                break

        if not ops:
            node_summaries.append({
                "node": node_name,
                "last_op": None,
                "rc": None,
                "op_status": None,
                "n_ops": 0,
                "has_shutdown": has_shutdown,
                "_ns_child_tags": ns_child_tags,
            })
            continue

        sorted_ops = sorted(ops, key=_safe_call_id)
        last = sorted_ops[-1]
        op = last.get("operation", "")
        rc = last.get("rc-code", "?")
        op_status = last.get("op-status", "0")

        node_summaries.append({
            "node": node_name,
            "last_op": op,
            "rc": rc,
            "op_status": op_status,
            "n_ops": len(ops),
            "has_shutdown": has_shutdown,
            "_ns_child_tags": ns_child_tags,
        })

        if op_status == "0" and rc == "0" and op in ("start", "monitor"):
            best_host = node_name

    return {
        "host": best_host,
        "has_any_ops": total_ops > 0,
        "node_summaries": node_summaries,
        "_debug_status_child_tags": status_child_tags,
    }


def _prim_is_disabled(prim: Any) -> bool:
    """True if the primitive has target-role=Stopped in its meta_attributes."""
    for meta in prim.iter("meta_attributes"):
        for nvpair in meta.findall("nvpair"):
            if nvpair.get("name") == "target-role" and nvpair.get("value", "").lower() == "stopped":
                return True
    return False


def _get_live_pacemaker_xml_debug() -> Dict[str, Any]:
    """Try live Pacemaker XML sources (API/CLI), including host-root binaries."""
    attempts: List[List[str]] = [
        ["cibadmin", "-Q"],
        ["/usr/sbin/cibadmin", "-Q"],
        ["/usr/bin/cibadmin", "-Q"],
        ["/proc/1/root/usr/sbin/cibadmin", "-Q"],
        ["/proc/1/root/usr/bin/cibadmin", "-Q"],
        ["crm_mon", "--as-xml", "-1"],
        ["/usr/sbin/crm_mon", "--as-xml", "-1"],
        ["/usr/bin/crm_mon", "--as-xml", "-1"],
        ["/proc/1/root/usr/sbin/crm_mon", "--as-xml", "-1"],
        ["/proc/1/root/usr/bin/crm_mon", "--as-xml", "-1"],
    ]
    debug_attempts: List[Dict[str, Any]] = []

    for cmd in attempts:
        res = _run_host_cmd(cmd, timeout=12)
        if "error" in res:
            debug_attempts.append({"cmd": " ".join(cmd), "error": res.get("error")})
            continue

        rc = int(res.get("returncode", 1))
        out = (res.get("stdout") or "")
        err = (res.get("stderr") or "")
        preview = (out if out else err)[:240]
        debug_attempts.append({
            "cmd": " ".join(cmd),
            "returncode": rc,
            "stdout_len": len(out),
            "stderr_len": len(err),
            "preview": preview,
        })

        if rc != 0:
            continue
        if "<" not in out or ">" not in out:
            continue
        try:
            root = ET.fromstring(out)
        except ET.ParseError:
            continue
        return {
            "xml": out,
            "source_cmd": " ".join(cmd),
            "root_tag": _xml_local_name(root.tag),
            "debug_attempts": debug_attempts,
        }

    return {
        "xml": None,
        "source_cmd": None,
        "root_tag": None,
        "debug_attempts": debug_attempts,
    }


def _get_status_from_pengine_debug() -> Dict[str, Any]:
    """Read latest pacemaker pengine input and extract <status> if present."""
    pengine_dirs = [
        Path("/var/lib/pacemaker/pengine"),
        Path("/run/pacemaker/pengine"),
        Path("/var/lib/pengine"),
    ]
    debug_attempts: List[Dict[str, Any]] = []
    candidates: List[Path] = []

    for d in pengine_dirs:
        if not d.exists():
            debug_attempts.append({"dir": str(d), "exists": False})
            continue
        debug_attempts.append({"dir": str(d), "exists": True})
        candidates.extend(sorted(d.glob("pe-input-*.bz2")))
        candidates.extend(sorted(d.glob("pe-input-*.xml")))

    if not candidates:
        return {"status_elt": None, "source_file": None, "debug_attempts": debug_attempts}

    # Most recent first
    candidates = sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)
    best_status_elt: Optional[Any] = None
    best_source_file: Optional[str] = None
    best_ops_count = -1

    for p in candidates[:20]:
        try:
            if p.suffix == ".bz2":
                raw = bz2.open(p, mode="rt", encoding="utf-8", errors="ignore").read()
            else:
                raw = p.read_text(errors="ignore")
        except OSError as exc:
            debug_attempts.append({"file": str(p), "error": str(exc)})
            continue

        try:
            root = ET.fromstring(raw)
        except ET.ParseError as exc:
            debug_attempts.append({"file": str(p), "parse_error": str(exc), "size": len(raw)})
            continue

        status_elt = _xml_find_first_by_local_name(root, "status")
        ops_count = 0
        if status_elt is not None:
            for elt in status_elt.iter():
                tag = _xml_local_name(elt.tag)
                if tag in ("lrm_rsc_op", "op_history"):
                    ops_count += 1

        debug_attempts.append({
            "file": str(p),
            "size": len(raw),
            "has_status": status_elt is not None,
            "ops_count": ops_count,
        })

        if status_elt is not None and ops_count > best_ops_count:
            best_ops_count = ops_count
            best_status_elt = status_elt
            best_source_file = str(p)

            # Good enough: plenty of operation history.
            if ops_count >= 10:
                break

    return {
        "status_elt": best_status_elt,
        "source_file": best_source_file,
        "debug_attempts": debug_attempts,
    }


def _get_cluster_info() -> Dict[str, Any]:
    # 1. Detect cluster mode via corosync.conf (mounted read-only from host)
    is_cluster = Path("/etc/corosync/corosync.conf").exists()
    if not is_cluster:
        return {"mode": "standalone", "online_nodes": [], "vms": []}

    # 2. Read CIB XML.
    # We prefer a CIB that contains a runtime <status> section.
    cib_xml: Optional[str] = None
    cib_root: Optional[Any] = None
    cib_source_path: Optional[str] = None
    cib_read_attempts: List[Dict[str, Any]] = []
    fallback_root: Optional[Any] = None
    fallback_xml: Optional[str] = None
    fallback_path: Optional[str] = None

    for p in CIB_PATHS:
        if not p.exists():
            continue
        try:
            raw = p.read_text()
        except OSError as exc:
            cib_read_attempts.append({"path": str(p), "error": str(exc)})
            continue

        try:
            parsed = ET.fromstring(raw)
        except ET.ParseError as exc:
            cib_read_attempts.append({"path": str(p), "parse_error": str(exc), "size": len(raw)})
            continue

        has_status = _xml_find_first_by_local_name(parsed, "status") is not None
        cib_read_attempts.append({"path": str(p), "size": len(raw), "has_status": has_status})
        if has_status:
            cib_xml = raw
            cib_root = parsed
            cib_source_path = str(p)
            break

        if fallback_root is None:
            fallback_root = parsed
            fallback_xml = raw
            fallback_path = str(p)

    if cib_root is None and fallback_root is not None:
        cib_root = fallback_root
        cib_xml = fallback_xml
        cib_source_path = fallback_path

    if not cib_xml or cib_root is None:
        return {
            "mode": "cluster",
            "error": (
                "Cluster détecté mais CIB inaccessible. "
                "Monter un CIB live, ex: "
                "Volume=/run/pacemaker/cib:/run/pacemaker/cib:ro"
            ),
            "online_nodes": [],
            "vms": [],
            "_debug_cib_read_attempts": cib_read_attempts,
        }

    # 3. Use selected CIB XML
    root = cib_root

    status_elt = _xml_find_first_by_local_name(root, "status")
    live_xml_debug: Dict[str, Any] = {"source_cmd": None, "root_tag": None, "debug_attempts": []}
    if status_elt is None:
        # Static cib.xml can omit runtime status. Try live Pacemaker XML query.
        live_xml_debug = _get_live_pacemaker_xml_debug()
        live_xml = live_xml_debug.get("xml")
        if live_xml:
            try:
                live_root = ET.fromstring(live_xml)
                live_status = _xml_find_first_by_local_name(live_root, "status")
                if live_status is not None:
                    status_elt = live_status
            except ET.ParseError:
                pass
    pengine_debug: Dict[str, Any] = {"source_file": None, "debug_attempts": []}
    if status_elt is None:
        pengine_debug = _get_status_from_pengine_debug()
        pengine_status = pengine_debug.get("status_elt")
        if pengine_status is not None:
            status_elt = pengine_status

    # Online nodes
    online_nodes: List[str] = []
    if status_elt is not None:
        for ns in _xml_find_all_by_local_name(status_elt, "node_state"):
            # Accept crmd=online OR in_ccm=true+join=member (pacemaker version variations)
            crmd_ok = ns.get("crmd") == "online"
            ccm_ok = ns.get("in_ccm") in ("true", "1") and ns.get("join") == "member"
            if crmd_ok or ccm_ok:
                name = ns.get("uname") or ns.get("id", "?")
                if name not in online_nodes:
                    online_nodes.append(name)

    # DC
    dc: Optional[str] = None
    dc_uuid = root.get("dc-uuid")
    if dc_uuid:
        config = _xml_find_first_by_local_name(root, "configuration")
        nodes_cfg = _xml_find_first_by_local_name(config, "nodes") if config is not None else None
        if nodes_cfg is not None:
            for node in _xml_find_all_by_local_name(nodes_cfg, "node"):
                if node.get("id") == dc_uuid:
                    dc = node.get("uname") or dc_uuid
                    break
        if dc is None:
            dc = dc_uuid

    # All VirtualDomain primitives with their status (CIB-only approach).
    vms: List[Dict] = []
    config = _xml_find_first_by_local_name(root, "configuration")
    if config is not None:
        resources_elt = _xml_find_first_by_local_name(config, "resources")
        if resources_elt is not None:
            for prim in _xml_find_all_by_local_name(resources_elt, "primitive"):
                if not (prim.get("class") == "ocf"
                        and prim.get("provider") == "seapath"
                        and prim.get("type") == "VirtualDomain"):
                    continue
                vm_id = prim.get("id", "?")
                disabled = _prim_is_disabled(prim)
                rsc_status = _cib_resource_status(status_elt, vm_id)
                host = rsc_status.get("host")

                state_source = "unknown"
                resolution_debug: Dict[str, Any] = {"disabled_in_cib": disabled}
                if disabled:
                    vm_state = "disabled"
                    state_source = "cib_meta_target_role"
                elif host:
                    vm_state = "started"
                    state_source = "cib_status_host"
                elif rsc_status.get("has_any_ops"):
                    vm_state = "stopped"
                    state_source = "cib_status_ops_no_running_host"
                elif rsc_status.get("node_summaries"):
                    vm_state = "unknown"
                    state_source = "cib_status_nodes_without_ops"
                else:
                    vm_state = "unknown"
                    state_source = "unknown"

                vms.append({
                    "name": vm_id,
                    "host": host,
                    "state": vm_state,
                    "_debug_state_source": state_source,
                    "_debug_resolution": resolution_debug,
                    "_debug_node_summaries": rsc_status.get("node_summaries", []),
                })

    # Debug: dump a preview of the raw <status> XML so we can inspect the real structure
    cib_status_preview: Optional[str] = None
    if status_elt is not None:
        try:
            raw = ET.tostring(status_elt, encoding="unicode")
            cib_status_preview = raw[:4000] + ("…" if len(raw) > 4000 else "")
        except Exception:
            pass

    return {
        "mode": "cluster",
        "dc": dc,
        "online_nodes": online_nodes,
        "vms": vms,
        "_debug_status_present": status_elt is not None,
        "_debug_cib_source_path": cib_source_path,
        "_debug_cib_read_attempts": cib_read_attempts,
        "_debug_root_children": sorted({_xml_local_name(c.tag) for c in root}),
        "_debug_live_xml_source_cmd": live_xml_debug.get("source_cmd"),
        "_debug_live_xml_root_tag": live_xml_debug.get("root_tag"),
        "_debug_live_xml_attempts": live_xml_debug.get("debug_attempts", []),
        "_debug_pengine_source_file": pengine_debug.get("source_file"),
        "_debug_pengine_attempts": pengine_debug.get("debug_attempts", []),
        "_cib_status_preview": cib_status_preview,
    }


def _get_vm_xml(vm_name: str) -> Optional[str]:
    result = _run_cmd(["rbd", "image-meta", "get", f"system_{vm_name}", "xml"], timeout=10)
    if "error" not in result and result.get("returncode", 1) == 0:
        return result.get("stdout", "").strip() or None
    return None


def _parse_vm_libvirt_xml(vm_name: str, xml_str: str, host: str) -> Dict[str, Any]:
    try:
        root = ET.fromstring(xml_str)
    except ET.ParseError as exc:
        return {"name": vm_name, "host": host, "error": f"XML parse error: {exc}", "all_vcpu_cpus": [], "emulatorpin_cpus": []}

    vcpu_elt = root.find("vcpu")
    vcpu_count = int(vcpu_elt.text) if vcpu_elt is not None and vcpu_elt.text else 0

    topology: Dict[str, int] = {}
    cpu_elt = root.find("cpu")
    if cpu_elt is not None:
        topo = cpu_elt.find("topology")
        if topo is not None:
            topology = {
                "sockets": int(topo.get("sockets", 1)),
                "dies": int(topo.get("dies", 1)),
                "cores": int(topo.get("cores", 1)),
                "threads": int(topo.get("threads", 1)),
            }

    cputune = root.find("cputune")
    vcpupins: List[Dict] = []
    emulatorpin_cpus: List[int] = []
    vcpuscheds: List[Dict] = []
    emulatorsched: Optional[Dict] = None

    if cputune is not None:
        for pin in cputune.findall("vcpupin"):
            cpuset_str = pin.get("cpuset", "")
            vcpupins.append({
                "vcpu": int(pin.get("vcpu", 0)),
                "cpus": _parse_cpuset(cpuset_str),
                "cpuset_str": cpuset_str,
            })
        empin = cputune.find("emulatorpin")
        if empin is not None:
            emulatorpin_cpus = _parse_cpuset(empin.get("cpuset", ""))
        for sched in cputune.findall("vcpusched"):
            vcpuscheds.append({
                "vcpus": sched.get("vcpus", ""),
                "scheduler": sched.get("scheduler", ""),
                "priority": int(sched.get("priority", 0)),
            })
        emsched = cputune.find("emulatorsched")
        if emsched is not None:
            emulatorsched = {
                "scheduler": emsched.get("scheduler", ""),
                "priority": int(emsched.get("priority", 0)),
            }

    all_vcpu_cpus = sorted(set(c for pin in vcpupins for c in pin["cpus"]))

    numatune: Dict[str, str] = {}
    nt = root.find("numatune")
    if nt is not None:
        mem = nt.find("memory")
        if mem is not None:
            numatune = {"mode": mem.get("mode", ""), "nodeset": mem.get("nodeset", "")}

    mem_elt = root.find("memory")
    memory_kb = int(mem_elt.text) if mem_elt is not None and mem_elt.text else 0

    return {
        "name": vm_name,
        "host": host,
        "vcpu_count": vcpu_count,
        "topology": topology,
        "vcpupins": vcpupins,
        "emulatorpin_cpus": emulatorpin_cpus,
        "all_vcpu_cpus": all_vcpu_cpus,
        "vcpuscheds": vcpuscheds,
        "emulatorsched": emulatorsched,
        "numatune": numatune,
        "memory_kb": memory_kb,
    }


def _get_hugepages_info() -> Dict[str, Any]:
    info: Dict[str, Any] = {}

    meminfo = Path("/proc/meminfo")
    if meminfo.exists():
        content = meminfo.read_text()
        for key in ("HugePages_Total", "HugePages_Free", "HugePages_Rsvd", "HugePages_Surp", "Hugepagesize"):
            m = re.search(rf"^{key}:\s+(\d+)", content, re.MULTILINE)
            if m:
                info[key.lower()] = int(m.group(1))

    gb_path = Path("/sys/kernel/mm/hugepages/hugepages-1048576kB/nr_hugepages")
    if gb_path.exists():
        try:
            info["nr_1g_hugepages"] = int(gb_path.read_text().strip())
        except ValueError:
            pass

    numa_nodes: List[Dict] = []
    node_dir = Path("/sys/devices/system/node")
    if node_dir.exists():
        for node_path in sorted(node_dir.glob("node*")):
            if not (node_path.is_dir() and re.match(r"node\d+$", node_path.name)):
                continue
            node_id = node_path.name.replace("node", "")
            hp_dir = node_path / "hugepages" / "hugepages-2048kB"
            if hp_dir.exists():
                ni: Dict[str, Any] = {"node": node_id}
                for fname in ("nr_hugepages", "free_hugepages", "surplus_hugepages"):
                    p = hp_dir / fname
                    if p.exists():
                        try:
                            ni[fname] = int(p.read_text().strip())
                        except ValueError:
                            pass
                numa_nodes.append(ni)
    if numa_nodes:
        info["numa_nodes"] = numa_nodes

    thp = Path("/sys/kernel/mm/transparent_hugepage/enabled")
    if thp.exists():
        info["thp_enabled"] = thp.read_text().strip()

    return info


def _get_rt_config_seapath() -> Dict[str, Any]:
    cfg: Dict[str, Any] = {}

    tuned_profile: Optional[str] = None
    for p in (Path("/run/tuned/active_profile"), Path("/etc/tuned/active_profile")):
        if p.exists():
            try:
                tuned_profile = p.read_text().strip()
                break
            except OSError:
                pass
    if tuned_profile is None:
        r = _run_cmd(["tuned-adm", "active"], timeout=5)
        if "error" not in r and r.get("returncode", 1) == 0:
            m = re.search(r"Current active profile:\s+(\S+)", r.get("stdout", ""))
            if m:
                tuned_profile = m.group(1)
    cfg["tuned_profile"] = tuned_profile

    if tuned_profile:
        for base in (Path("/etc/tuned"), Path("/usr/lib/tuned")):
            profile_dir = base / tuned_profile
            if not profile_dir.exists():
                continue
            tuned_conf = profile_dir / "tuned.conf"
            if tuned_conf.exists():
                try:
                    cfg["tuned_conf"] = tuned_conf.read_text()
                except OSError:
                    pass
            scripts = []
            for sh in sorted(profile_dir.glob("*.sh")):
                try:
                    scripts.append({"name": sh.name, "content": sh.read_text()})
                except OSError:
                    pass
            if scripts:
                cfg["tuned_scripts"] = scripts
            break

    cfg["isolated_cpus"] = detect_isolated_cpus()

    cmdline_path = Path("/proc/cmdline")
    if cmdline_path.exists():
        cfg["cmdline"] = cmdline_path.read_text().strip()

    sysctl: Dict[str, str] = {}
    for path_suffix, key in (
        ("kernel/sched_rt_runtime_us", "kernel.sched_rt_runtime_us"),
        ("kernel/sched_rt_period_us", "kernel.sched_rt_period_us"),
        ("kernel/numa_balancing", "kernel.numa_balancing"),
        ("kernel/nmi_watchdog", "kernel.nmi_watchdog"),
        ("kernel/watchdog", "kernel.watchdog"),
        ("vm/swappiness", "vm.swappiness"),
        ("vm/stat_interval", "vm.stat_interval"),
        ("kernel/sched_min_granularity_ns", "kernel.sched_min_granularity_ns"),
        ("kernel/sched_wakeup_granularity_ns", "kernel.sched_wakeup_granularity_ns"),
    ):
        p = Path(f"/proc/sys/{path_suffix}")
        if p.exists():
            try:
                sysctl[key] = p.read_text().strip()
            except OSError:
                pass
    cfg["sysctl"] = sysctl
    return cfg


def run_seapath_checks() -> Dict[str, Any]:
    cluster = _get_cluster_info()

    vms_detailed: List[Dict] = []
    for vm in cluster.get("vms", []):
        xml_str = _get_vm_xml(vm["name"])
        base = {
            "state": vm.get("state", "unknown"),
            "_debug_node_summaries": vm.get("_debug_node_summaries", []),
        }
        if xml_str:
            parsed = _parse_vm_libvirt_xml(vm["name"], xml_str, vm.get("host"))
            parsed.update(base)
        else:
            parsed = {
                "name": vm["name"],
                "host": vm.get("host"),
                "error": "XML non disponible (rbd image-meta get a échoué)",
                "all_vcpu_cpus": [], "emulatorpin_cpus": [],
                **base,
            }
        vms_detailed.append(parsed)

    all_cpus = _get_all_cpus()
    cpu_topology = _get_cpu_topology(all_cpus)
    isolated_cpus = detect_isolated_cpus()

    cpu_assignment: Dict[int, Dict] = {cpu: {"vms_vcpu": [], "vms_emulator": []} for cpu in all_cpus}
    for vm in vms_detailed:
        # Only include started VMs in the CPU map
        if vm.get("state") != "started":
            continue
        name = vm["name"]
        for cpu in vm.get("all_vcpu_cpus", []):
            if cpu in cpu_assignment:
                cpu_assignment[cpu]["vms_vcpu"].append(name)
        for cpu in vm.get("emulatorpin_cpus", []):
            if cpu in cpu_assignment:
                cpu_assignment[cpu]["vms_emulator"].append(name)

    cpu_map: List[Dict] = []
    for cpu in all_cpus:
        entry = cpu_assignment[cpu]
        vms_v = entry["vms_vcpu"]
        vms_e = entry["vms_emulator"]
        all_vms = sorted(set(vms_v + vms_e))
        is_isolated = cpu in isolated_cpus
        siblings = cpu_topology.get(cpu, {}).get("thread_siblings", [cpu])
        sibling_occupied: List[int] = []
        for sib in siblings:
            if sib == cpu:
                continue
            sib_entry = cpu_assignment.get(sib, {"vms_vcpu": [], "vms_emulator": []})
            if sib_entry["vms_vcpu"] or sib_entry["vms_emulator"]:
                sibling_occupied.append(sib)
        conflict = len(set(vms_v)) > 1
        overlap = bool(vms_v and vms_e and not set(vms_v).issuperset(set(vms_e)))

        if conflict:
            status = "conflict"
        elif overlap:
            status = "overlap"
        elif vms_v:
            status = "vcpu"
        elif vms_e:
            status = "emulator"
        elif is_isolated and sibling_occupied:
            status = "isolated_ht_busy"
        elif is_isolated:
            status = "isolated_free"
        else:
            status = "free"

        cpu_map.append({
            "cpu": cpu, "status": status,
            "vms_vcpu": vms_v, "vms_emulator": vms_e,
            "all_vms": all_vms, "is_isolated": is_isolated,
            "thread_siblings": siblings,
            "sibling_occupied_cpus": sibling_occupied,
            "topology": cpu_topology.get(cpu, {}),
        })

    return {
        "cluster": cluster,
        "vms": vms_detailed,
        "rt_config": _get_rt_config_seapath(),
        "hugepages": _get_hugepages_info(),
        "cpu_map": cpu_map,
        "cpu_topology": cpu_topology,
        "all_cpus": all_cpus,
        "isolated_cpus": isolated_cpus,
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


@app.get("/seapath", response_class=HTMLResponse)
async def seapath_page(request: Request) -> HTMLResponse:
    lang = get_lang_from_request(request)
    return templates.TemplateResponse(
        "seapath.html",
        {"request": request, "lang": lang, "active_tab": "seapath"},
    )


@app.get("/api/seapath/run")
async def seapath_run():
    data = run_seapath_checks()
    return JSONResponse(data)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


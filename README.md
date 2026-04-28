# rtperfui

Web application in Python (FastAPI) that provides a frontend to run real‑time performance tests on the host.

## Current features

- Modern web UI (Tailwind, Chart.js).
- **Internationalisation (French / English)**:
  - Automatic detection via the `Accept-Language` header.
  - FR/EN toggle in the header to explicitly force the language.

- **`cyclictest` tab**:
  - Form to run `cyclictest` with the following parameters:
    - **Duration** in seconds (default: 60).
    - **Interval** in µs (default: 200).
    - **RT priority** (SCHED_FIFO, default: 90).
    - **Scheduling policy** (FIFO or RR).
    - **CPU affinity** (comma‑separated list of CPUs, default: detected isolated CPUs).
    - **Distance** `-d` (µs, default: 200, `0` to disable).
  - Automatic detection of isolated CPUs via `/sys/devices/system/cpu/isolated`
    (fallback to all online CPUs except CPU0).
  - Runs `cyclictest` on the host and parses the output (including Debian histogram format).
  - Displays a **latency histogram** on a **logarithmic Y‑axis**, with:
    - One dataset (bar series) per CPU/thread (distinct color).
    - Per‑CPU min/avg/max summary + number of samples.

- **`hwlatdetect` tab**:
  - Form to run `hwlatdetect` with:
    - Duration, window, width, threshold.
  - Parses the output (`inner`/`outer`, summary lines).
  - Line graph of latencies + min/avg/max summary.
  - The “no samples above threshold” case is treated as **OK** (informational status, not an error).

- **`systemcheck` tab**:
  - Single button that runs a series of host checks:
    - **tuned** profile (`tuned-adm active`).
    - **CPU isolation** (isolated CPUs).
    - **Hyperthreading/SMT** (`/sys/devices/system/cpu/smt/active`).
    - Kernel preemption (**PREEMPT_RT** vs PREEMPT).
    - Boot parameters (`/proc/cmdline`): `nohz_full`, `rcu_nocbs`, C‑states limits, etc.
    - RT sysctl parameters (`sched_rt_runtime_us`, `sched_rt_period_us`).
    - **ACPI** presence/state.
    - Hugepages / **Transparent Huge Pages**.
    - IRQ affinity (pointer to `/proc/irq/*/smp_affinity`).
    - **PTP** clock presence (`/sys/class/ptp`).
  - Detailed report with status per check (`OK`, `WARNING`, `INFO`, etc.).

- **`seapath` tab**:
  - Single button that analyses the Seapath configuration of the host:
    - **Cluster / standalone detection** via `/etc/corosync/corosync.conf`.
    - In cluster mode: reads the Pacemaker CIB (runtime `/run/pacemaker/cib/cib.xml` preferred,
      falls back to `/var/lib/pacemaker/cib/cib.xml`, live `cibadmin -Q`, `crm_mon --as-xml`,
      or the latest pengine input file).
    - Lists all `ocf:seapath:VirtualDomain` resources with their state (`started`, `stopped`,
      `disabled`, `unknown`) and the node they run on.
    - **RT configuration**: active tuned profile (with key `tuned.conf` sections), isolated CPUs,
      boot cmdline (RT‑relevant parameters highlighted), and RT sysctl values.
    - **Hugepages**: 2 MiB / 1 GiB counts, per‑NUMA breakdown, THP status.
    - **Interactive CPU map**: color‑coded grid (one cell per logical CPU) showing which VM each
      CPU is assigned to (vCPU pin or emulatorpin), free/isolated/HT‑conflict state.
      Cells are grouped by physical core (package × core) to visualise Hyper‑Threading pairs.
    - **VM detail cards**: per‑VM vCPU topology, vcpupin / emulatorpin table, RT scheduling
      (vcpusched / emulatorsched priorities), NUMA policy, and memory size.
    - Toggle to show or hide disabled VMs across all views.
    - When running inside a container, falls back to `nsenter` into PID‑1 namespaces to reach
      host‑only binaries (`cibadmin`, `rbd`, etc.).

## Requirements

- Python 3.10+ recommended.
- `cyclictest` installed on the host (package `rt-tests` on most Linux distros).
- Sufficient privileges to run real‑time tasks (often `root` or appropriate RT capabilities).
- **For the Seapath tab (optional):**
  - `rbd` (package `ceph-common`) — to retrieve per‑VM libvirt XML from Ceph RBD metadata.
  - `cibadmin` or `crm_mon` — to query the live Pacemaker CIB (only needed if no CIB file is
    accessible at `/run/pacemaker/cib/cib.xml` or `/var/lib/pacemaker/cib/cib.xml`).
  - Read access to `/etc/corosync/corosync.conf` (cluster detection) and `/etc/ceph` (RBD auth).

## Installation (bare metal)

```bash
cd rtperfui
python -m venv .venv
source .venv/bin/activate  # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Running the application

From the project root:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Then open `http://localhost:8000` in your browser.

## `cyclictest` tab usage

1. Open the main page (`/`).
2. Check / adjust default parameters:
   - Duration: 60 s
   - Interval: 200 µs
   - Priority: 90 (SCHED_FIFO)
   - CPU affinity: left empty → uses detected isolated CPUs (or fallback set).
3. Click **Run test**.
4. After the test completes:
   - A latency histogram per CPU is displayed (logarithmic Y scale).
   - A per‑CPU summary (min / avg / max / samples) is shown above the chart.

If `cyclictest` is not found or returns an error, an explicit error message is shown below the form.

## Other tabs

- **hwlatdetect**:
  - Open the `hwlatdetect` tab.
  - Adjust duration / window / width / threshold as needed.
  - Run the test, then inspect:
    - The latency line chart when there are samples.
    - The summary, which clearly indicates when there are no samples above the threshold.

- **systemcheck**:
  - Open the `systemcheck` tab.
  - Click **Run checks**.
  - Read the report:
    - Each card corresponds to a specific RT configuration aspect.
    - Badge color (`OK`, `WARNING`, `INFO`) helps quickly spot items that may need attention.

- **seapath**:
  - Open the `seapath` tab.
  - Click **Analyze**.
  - The page displays four sections: cluster status, RT configuration, hugepages, CPU map, and VM
    detail cards.
  - Disabled VMs are hidden by default; use the toggle above the VM cards to show them.

## Containerisation (Docker / Podman)

A `Dockerfile` is provided to build a self‑contained image including:

- Python + dependencies (`requirements.txt`).
- The FastAPI application + templates.
- `rt-tests` (to have `cyclictest`, `hwlatdetect`, etc. inside the container).

### Build the image

```bash
cd rtperfui
podman build -t rtperfui:latest .
# or
docker build -t rtperfui:latest .
```

The image exposes port **8000** and runs:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Simple run (no Quadlet)

```bash
podman run --rm -p 8000:8000 \
  --privileged \
  --cap-add=SYS_NICE \
  --ulimit rtprio=99 \
  --ulimit memlock=-1 \
  -v /sys:/sys \
  -v /run/tuned:/run/tuned:ro \
  -v /etc/tuned:/etc/tuned:ro \
  -v /dev/cpu_dma_latency:/dev/cpu_dma_latency \
  -v /run:/run:ro \
  -v /var/lib/pacemaker:/var/lib/pacemaker:ro \
  -v /etc/corosync/corosync.conf:/etc/corosync/corosync.conf:ro \
  -v /etc/ceph:/etc/ceph:ro \
  rtperfui:latest
```

> **Note:** `/proc` is **not** mounted explicitly. In a `--privileged` container, the container's
> own `/proc` already reflects host kernel values for non‑namespaced paths (`cmdline`, `cpuinfo`,
> `meminfo`, `sys/kernel/*`, `sys/vm/*`, `irq`, etc.). Mounting `/proc` wholesale breaks `runc`
> network initialisation (read‑only filesystem error).

Then open `http://localhost:8000`.

## Quadlet (Podman + systemd)

An example Quadlet file is provided: `rtperfui.container`.

Contents:

```ini
[Unit]
Description=rtperfui real-time test UI container

[Container]
Image=docker.io/insatomcat/rtperfui:latest
ContainerName=rtperfui
PublishPort=8000:8000
User=root

# Capabilities / ulimits for real-time
PodmanArgs=--privileged
AddCapability=CAP_SYS_NICE
Ulimit=rtprio=99
Ulimit=memlock=-1

# Expose host sysfs needed for checks and RT tools
# Note: /proc is NOT mounted — a --privileged container's own /proc already
# reflects host kernel values; mounting it wholesale breaks runc network init.
Volume=/sys:/sys
Volume=/run/tuned:/run/tuned:ro
Volume=/etc/tuned:/etc/tuned:ro
Volume=/dev/cpu_dma_latency:/dev/cpu_dma_latency

# Runtime directories (covers pacemaker variants under /run/*)
Volume=/run:/run:ro
# Pacemaker state (CIB + pengine inputs) — needed for Seapath tab
Volume=/var/lib/pacemaker:/var/lib/pacemaker:ro
# Corosync config — used to detect cluster mode
Volume=/etc/corosync/corosync.conf:/etc/corosync/corosync.conf:ro
# Ceph config + keyring — needed for rbd image-meta get (VM XML retrieval)
Volume=/etc/ceph:/etc/ceph:ro

Environment=PYTHONUNBUFFERED=1
[Service]
Restart=always

[Install]
WantedBy=default.target
```

### Installation (user systemd / Podman Quadlet)

1. Copy the file into the user Quadlet directory:

   ```bash
   mkdir -p ~/.config/containers/systemd
   cp rtperfui.container ~/.config/containers/systemd/
   ```

2. Reload systemd (user session) and start the service:

   ```bash
   systemctl --user daemon-reload
   systemctl --user enable --now rtperfui.service
   ```

3. The application will then listen on host port 8000, with:
   - `CAP_SYS_NICE` and RT‑friendly `ulimit` values.
   - Read‑only access to `/sys` and `/proc` for system checks.
   - Access to `/dev/cpu_dma_latency` to pin CPU DMA latency.

## Possible roadmap

- Additional tabs for other RT tests.
- Real‑time streaming of measurements (WebSocket or SSE).
- Export of results (JSON/CSV).
- More advanced `cyclictest` options (multi‑threads, detailed histograms, etc.).
- Seapath: live VM migration tracking and per‑node CPU assignment comparison.


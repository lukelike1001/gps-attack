# gps-attack

Replication of Hakani et al., "Evaluation and Telemetry-Based Detection of GPS Spoofing Effects
on UAV Navigation Using Software-Defined Radio," *Scientific Reports*, May 2026.

A drone flies an autonomous waypoint mission in ArduPilot SITL. Mid-flight, a Python hook
injects fake GPS coordinates via MAVLink `GPS_INPUT` messages. The drone deviates, breaches
a geofence, and triggers automatic RTL. Telemetry logs capture anomalies in barometric altitude,
yaw, magnetometer, and HDOP compared to a baseline flight.

---

## Repository layout

```
gps-attack/
├── docker/
│   ├── Dockerfile              Two-stage build: SITL builder → lightweight runtime
│   ├── entrypoint.sh           Starts sim_vehicle.py with env-derived port flags
│   └── docker.env              All tunable Docker values (branch, ports)
├── sim/
│   ├── baseline_waypoints.plan QGroundControl waypoint mission + geofence
│   ├── sitl_params.yaml        Tunable SITL connection and parameter values
│   └── configure_sitl.py       Sets ArduPilot SITL parameters via MAVLink
├── attack/
│   └── gps_hook.py             GPS_INPUT injection hook (REPLAY-01)
├── analysis/
│   └── plot_telemetry.py       .bin log extraction + comparison plots (PLOT-01)
├── logs/                       .bin flight logs land here (bind-mounted into container)
├── docker-compose.yml          Single-command container orchestration
├── requirements.txt            Python project dependencies
└── DESIGN_PRACTICES.md
```

---

## Local Quickstart (recommended for development)

Tested on Ubuntu 22.04. All commands run from the repo root unless noted.

### 1. Clone and build ArduPilot SITL

Clone ArduPilot to `~/ardupilot`, outside this repo so its lifecycle stays independent.

```bash
git clone --branch Copter-4.6.3 --recursive https://github.com/ArduPilot/ardupilot.git ~/ardupilot
cd ~/ardupilot
Tools/environment_install/install-prereqs-ubuntu.sh -y
```

`sim_vehicle.py` and `mavproxy.py` need to be on `PATH`. Rather than scattering exports
through `~/.bashrc`, keep them in one dedicated profile and source it from `~/.bashrc`:

```bash
cat > ~/.ardupilot_profile << 'EOF'
# ArduPilot SITL tooling for gps-attack local development.
# sim_vehicle.py lives in the clone; mavproxy.py is pip-installed to ~/.local/bin.
export PATH="$HOME/ardupilot/Tools/autotest:$HOME/.local/bin:$PATH"
EOF

cat >> ~/.bashrc << 'EOF'

if [ -f ~/.ardupilot_profile ]; then
    source ~/.ardupilot_profile
fi
EOF
```

Open a new terminal and verify:

```bash
which sim_vehicle.py
which mavproxy.py
```

### 2. Install Python dependencies

From the repo root (not the ardupilot directory):

```bash
pip3 install -r requirements.txt --break-system-packages
```

Dependencies: `pymavlink`, `pyyaml`, `matplotlib`, `numpy`.

### 3. Install QGroundControl

Download the latest AppImage from the
[QGroundControl daily builds](https://docs.qgroundcontrol.com/master/en/qgc-user-guide/getting_started/download_and_install.html)
page, then make it executable:

```bash
chmod +x QGroundControl-x86_64.AppImage
./QGroundControl-x86_64.AppImage
```

### Removing the local setup

If you no longer need to use or prototype with the `gps-attack` repo, you can remove the local setup by following these instructions.

```bash
rm ~/.ardupilot_profile
```

Then delete this block from the end of `~/.bashrc`:

```bash
if [ -f ~/.ardupilot_profile ]; then
    source ~/.ardupilot_profile
fi
```

---

## AUTO-01 — Clean waypoint mission

### 4. Start SITL

Open a dedicated terminal in the repo root. `sim_vehicle.py` is an executable installed
on your PATH by the prereqs script. Do not prefix it with `python`. SITL binds two
MAVLink outputs: UDP 14550 for QGroundControl, UDP 14551 for the Python scripts.

```bash
sim_vehicle.py -v ArduCopter \
    --out udp:127.0.0.1:14550 \
    --out udp:127.0.0.1:14551
```

Wait until the console prints `APM: EKF3 IMU0 is using GPS` before proceeding — the
simulated GPS fix is required for arming. The vehicle spawns near Canberra, Australia
(-35.36°, 149.17°).

### 5. Apply baseline parameters

In a second terminal:

```bash
python3 sim/configure_sitl.py --mode baseline
```

This enables a 200 m inclusion geofence with RTL on breach. All parameter values are
defined in `sim/sitl_params.yaml`.

### 6. Load the waypoint mission

1. Open QGroundControl. It auto-connects to SITL on UDP 14550.
2. Go to **Plan** view.
3. Click the file icon → **Open** → select `sim/baseline_waypoints.plan`.
4. Click **Upload** to send the mission and geofence to SITL.

### 7. Arm and fly

In QGroundControl **Fly** view, slider-arm the vehicle and click **Start Mission**.

Expected: drone takes off to 30 m, flies a four-waypoint square (~100 m sides), RTLs
home. No fence breach alert fires.

### 8. Retrieve the .bin log

ArduPilot SITL writes `.bin` DataFlash logs to the `logs/` subdirectory of wherever
`sim_vehicle.py` was launched. After landing:

```bash
ls -lt logs/*.BIN | head -3
cp $(ls -t logs/*.BIN | head -1) logs/baseline_flight.bin
```

AUTO-01 is complete when `logs/baseline_flight.bin` exists and the QGroundControl map
shows a clean rectangular path with no geofence breach.

---

## REPLAY-01 — GPS spoofing mid-flight

> **Do not proceed until AUTO-01 passes.**

Apply attack parameters (adds `GPS1_TYPE=14`, `GPS_AUTO_SWITCH=0`, `EK3_GPS_TYPE=3`):

```bash
python3 sim/configure_sitl.py --mode attack
```

Reboot SITL (type `reboot` in the SITL console), then run the GPS hook:

```bash
python3 attack/gps_hook.py
```

---

## LOG-01 — Telemetry logging

SITL writes `.bin` logs into the `logs/` directory. Copy both logs under consistent names:

```bash
cp $(ls -t logs/*.BIN | head -1) logs/baseline_flight.bin
cp $(ls -t logs/*.BIN | head -2 | tail -1) logs/spoofed_flight.bin
```

---

## PLOT-01 — Comparison plots

```bash
python3 analysis/plot_telemetry.py \
    logs/baseline_flight.bin \
    logs/spoofed_flight.bin
```

Produces side-by-side plots of barometric altitude, yaw, magnetometer, and HDOP.

---

## Docker setup (optional)

<details>
<summary>Expand for Docker instructions</summary>

> **First build takes 20–30 minutes** while ArduPilot SITL compiles. Subsequent builds
> reuse the cached layer.

### Build and start the container

```bash
docker compose up --build -d
```

SITL starts automatically. Tail its output with:

```bash
docker compose logs -f
```

Wait until you see `APM: EKF3 IMU0 is using GPS`.

### Open QGroundControl on the host

Launch QGroundControl. It auto-connects to SITL via UDP 14550 on localhost.

### Apply parameters

```bash
# Baseline
docker compose exec ardupilot-sitl python3 sim/configure_sitl.py --mode baseline

# Attack (after baseline flight completes)
docker compose exec ardupilot-sitl python3 sim/configure_sitl.py --mode attack
```

### Run the GPS hook

```bash
docker compose exec ardupilot-sitl python3 attack/gps_hook.py
```

### Retrieve logs

Logs are bind-mounted to `logs/` on the host:

```bash
ls -lt logs/*.BIN | head -3
```

### Stop the container

```bash
docker compose down
```

</details>

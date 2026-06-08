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

Tested on Ubuntu 22.04. All commands run from the repo root unless noted. You only need to run these steps once to c

### Step 1: Clone and build ArduPilot SITL

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

### Step 2: Install Python dependencies

From the repo root (not the ardupilot directory):

```bash
pip3 install -r requirements.txt --break-system-packages
```

Dependencies: `pymavlink`, `pyyaml`, `matplotlib`, `numpy`.

### Step 3: Install QGroundControl

Download the latest AppImage from the
[QGroundControl daily builds](https://docs.qgroundcontrol.com/master/en/qgc-user-guide/getting_started/download_and_install.html)
page, then make it executable:

```bash
chmod +x QGroundControl-x86_64.AppImage
./QGroundControl-x86_64.AppImage
```

After opening QGroundControl and verifying that the GUI loads, you can close it for now.

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

## AUTO-01: Clean waypoint mission

### Step 1: Start SITL

Open a dedicated terminal in the repo root. `sim_vehicle.py` is an executable installed on your PATH by the prereqs script. Do not prefix it with `python`. SITL binds two MAVLink outputs: UDP 14550 for QGroundControl, UDP 14551 for the Python scripts.

```bash
sim_vehicle.py -v ArduCopter \
    --out udp:127.0.0.1:14550 \
    --out udp:127.0.0.1:14551
```

**CRITICAL STEP**: Wait until the console prints `APM: EKF3 IMU0 is using GPS` before proceeding, because the simulated GPS fix is required for arming. The vehicle spawns near Canberra, Australia
(-35.36°, 149.17°).

### Step 2: Apply baseline parameters

In a second terminal:

```bash
python3 sim/configure_sitl.py --mode baseline
```

This enables a 200m inclusion geofence with RTL on breach. All parameter values are defined in `sim/sitl_params.yaml`.

### Step 3: Load the waypoint mission

1. Open QGroundControl by running `./QGroundControl-x86_64.AppImage`. It auto-connects to SITL on UDP 14550.
2. Go to **Plan** view.
3. Click the file icon → **Open** → select `sim/baseline_waypoints.plan`.
4. Click **Upload** to send the mission and geofence to SITL.

### Step 4: Arm and fly

In QGroundControl **Fly** view, hold the **Start Mission** slider-arm button.

**Expected:** drone takes off to 30 m, flies a four-waypoint square (~100 m sides), RTLs home. No fence breach alert fires.

### Step 5: Retrieve the .bin log

ArduPilot SITL writes `.bin` DataFlash logs to the `logs/` subdirectory of wherever `sim_vehicle.py` was launched. After landing:

```bash
ls -lt logs/*.BIN | head -3
cp $(ls -t logs/*.BIN | head -1) logs/baseline_flight.bin
```

AUTO-01 is complete when `logs/baseline_flight.bin` exists and the QGroundControl map shows a clean rectangular path with no geofence breach.

---

## REPLAY-01: GPS spoofing mid-flight

> **Warning: You should not run this code until AUTO-01 passes.**

Next, we will modify the baseline flight to perform GPS spoofing mid=flight. We will apply the following attack parameters (adds `GPS1_TYPE=14` and `GPS_AUTO_SWITCH=0`) in this demo.

### Step 1: Run the SITL

Boot up the SITL using the same script provided in AUTO-01. If you just finished running Step 5 in AUTO-01 and have not ended the `sim_vehicle.py` session, then you do not need to run this script again.

```bash
sim_vehicle.py -v ArduCopter \
    --out udp:127.0.0.1:14550 \
    --out udp:127.0.0.1:14551
```

### Step 2: Enter GPS spoofing attack mode

In a new terminal, you should run the following script to switch from the `baseline` to `attack` mode.

```bash
python3 sim/configure_sitl.py --mode attack
```

By this point, you should have Terminal 1 running `sim_vehicle.py` and Terminal 2 running this `configure.sitl.py` file.

### Step 3: Reboot SITL

Type `reboot` in the Terminal 1 (the SITL console). Then, move to Terminal 2 and run the GPS hook:

```bash
python3 attack/gps_hook.py
```

### Step 4: Observe via QGroundControl

Run QGroundControl to observe the GPS spoofing flight. If you have already opened QGroundControl and haven't closed it since AUTO-01, you do not need to re-open it.

```bash
./QGroundControl-x86_64.AppImage
```

### Step 5: Save the spoofed log

Similar to AUTO-01, the spoofed flight has already been saved, but you can rename it for readability.

```bash
ls -lt logs/*.BIN | head -3
cp $(ls -t logs/*.BIN | head -1) logs/spoofed_flight.bin
```

### Optional: Cleaning Persistent ArduPilot Parameters
ArduPilot persists parameters across launches via `eeprom.bin` in the launch directory. `--mode baseline` only re-applies the fence parameters, and it does **not** reset the GPS-related parameters set by `--mode attack` (`GPS1_TYPE`, `GPS_AUTO_SWITCH`, `EK3_GPS_TYPE`).

To fix the `PreArm: GPS 1: Bad fix` / `Fence requires position` error, run this script in Terminal 2:

```bash
python3 sim/configure_sitl.py --mode baseline
```

Then, run this script in Terminal 1 (in the `sim_vehicle.py` input):
```
param set GPS1_TYPE 1
param set GPS_AUTO_SWITCH 1
reboot
```

Wait for `APM: EKF3 IMU0 is using GPS` to reappear before arming.

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

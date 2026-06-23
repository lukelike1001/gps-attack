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
├── plans/
│   ├── canberra.plan           QGroundControl waypoint mission + geofence (Canberra, AU)
│   └── ornl.plan               QGroundControl waypoint mission + geofence (ORNL, TN)
├── sim/
│   ├── scenario_params.yaml    Tunable SITL scenario parameter values
│   └── load_scenario.py        Sets ArduPilot scenario parameters via MAVLink
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

## Local Installation

Tested on Ubuntu 22.04. All commands run from the repo root unless noted. You only need to run these steps once to c

### Step 1: Clone and build ArduPilot SITL

Clone ArduPilot to `~/ardupilot`, outside this repo so its lifecycle stays independent.

```bash
git clone --branch Copter-4.6.3 --recursive https://github.com/ArduPilot/ardupilot.git ~/ardupilot
cd ~/ardupilot
Tools/environment_install/install-prereqs-ubuntu.sh -y
```

`sim_vehicle.py` and `mavproxy.py` need to be on `PATH`. Rather than scattering exports through `~/.bashrc`, keep them in one dedicated profile and source it from `~/.bashrc`:

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

## Quickstart: `run_simulation.sh`

```bash
./run_simulation.sh --attack-type passthrough --spawn-location ornl
./run_simulation.sh --attack-type dynamic --spawn-location canberra
```

Run the script, then open QGroundControl with the matching `.plan` file. Then, arm the flight and start the mission to run the selected mission.

---

## AUTO-01: Clean waypoint mission

### Step 1: Start SITL

Open a dedicated terminal in the repo root. `sim_vehicle.py` is an executable installed on your PATH by the prereqs script. Do not prefix it with `python`. SITL binds two MAVLink outputs: UDP 14550 for QGroundControl, UDP 14551 for the Python scripts.

```bash
sim_vehicle.py -v ArduCopter \
    --custom-location=35.93051398,-84.31067453,50,0 \
    --out udp:127.0.0.1:14550 \
    --out udp:127.0.0.1:14551
```

You should see a new `ArduCopter` window pop up.
<p align="center">
    <img src="icons/arducopter.png" alt="ArduCopter Window" width="400">
</p>

**NOTE:** For questions about how ArduPilot formats `custom-location`, see [DEBUG_FAQ.md](DEBUG_FAQ.md#ardupilot-custom-location-formatting).

### Step 2: Apply baseline parameters

In a different terminal (Terminal 2):

```bash
python3 simulation/run_simulation.py --attack-type passthrough --spawn-location ornl
```

This script starts the GPS attack simulation, with a specified attack type and a spawn location.

### Step 3: Open QGroundControl

Open QGroundControl in another terminal (Terminal 3).

```bash
./QGroundControl-x86_64.AppImage
```

It auto-connects to SITL on UDP 14550.

### Step 4: Configure QGroundControl.

Inside QGroundControl, use the GUI and apply the following steps:

a. <img src="icons/qgroundcontrol_plan.png" alt="Plan" width="100"> Go to **Plan** view. (Click the "Q" icon in the top-left corner for the drop-down.)

b. <img src="icons/qgroundcontrol_open.png" alt="Open" width="100"> Click the file icon → **Open** → select `plans/ornl.plan`

c. <img src="icons/qgroundcontrol_upload.png" alt="Upload" width="100"> Click **Upload** to send the mission and geofence to SITL.

### Step 5: Arm and fly

**CRITICAL STEP**: Wait until the console prints `APM: EKF3 IMU0 is using GPS` before proceeding, because the simulated GPS fix is required for arming. The vehicle spawns near Oak Ridge, TN (35.93°, -84.31°) See [DEBUG_FAQ.md](DEBUG_FAQ.md#ornl-baseline-flight-is-not-ready) if you see a yellow "Not Ready" message.

In QGroundControl **Fly** view, hold the **Start Mission** slider-arm button.

![ORNL Arm and Fly](icons/ornl_arm_and_fly.png)

**Expected:** drone takes off to 50m, flies to all waypoints, then RTLs home. No fence breach alert fires.

### Step 6: Retrieve the .bin log

Wait for the flight to finish in QGroundControl.

![ORNL Finished Flight](icons/ornl_finished_flight.png)

ArduPilot SITL writes `.bin` DataFlash logs to the `logs/` subdirectory of wherever `sim_vehicle.py` was launched. After landing:

```bash
mkdir -p logs/ornl
ls -lt logs/*.BIN | head -3
cp $(ls -t logs/*.BIN | head -1) logs/ornl/baseline_flight.bin
```

AUTO-01 is complete when `logs/ornl/baseline_flight.bin` exists and the QGroundControl map shows a clean rectangular path with no geofence breach.

---

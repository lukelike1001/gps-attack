#!/bin/bash
# Master entry point: launch SITL + apply parameters + (optionally) run the
# GPS spoofing attack for a given preset location.
#
# Usage: ./run_simulation.sh --mode {baseline|static|dynamic} --preset {ornl|canberra}
set -euo pipefail

usage() {
    echo "Usage: $0 --mode {baseline|static|dynamic} --preset {ornl|canberra}" >&2
    exit 1
}

MODE=""
PRESET=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --mode) MODE="$2"; shift 2 ;;
        --preset) PRESET="$2"; shift 2 ;;
        *) echo "Unknown argument: $1" >&2; usage ;;
    esac
done

case "$MODE" in
    baseline|static|dynamic) ;;
    *) echo "Invalid --mode: '$MODE'" >&2; usage ;;
esac

case "$PRESET" in
    ornl|canberra) ;;
    *) echo "Invalid --preset: '$PRESET'" >&2; usage ;;
esac

cd "$(dirname "$0")"

bash clear_persistent.sh
mkdir -p logs

PRESET_CONFIG="attack/presets/${PRESET}.yaml"

read -r LAT LON ALT < <(python3 -c "
import yaml
home = yaml.safe_load(open('${PRESET_CONFIG}'))['home_position']
print(home['lat'], home['lon'], home['alt'])
")

SITL_LOG="logs/${MODE}_${PRESET}.log"
echo "Starting SITL (${PRESET}) at ${LAT},${LON},${ALT}. Log: ${SITL_LOG}"
sim_vehicle.py -v ArduCopter \
    --custom-location="${LAT},${LON},${ALT},0" \
    --out udp:127.0.0.1:14550 \
    --out udp:127.0.0.1:14551 \
    > "$SITL_LOG" 2>&1 < <(tail -f /dev/null) &
SITL_PID=$!

if [[ "$MODE" == "baseline" ]]; then
    python3 sim/load_scenario.py --mode baseline --reboot
else
    python3 sim/load_scenario.py --mode attack --reboot
    if [[ "$MODE" == "static" ]]; then
        python3 attack/gps_hook.py --config "$PRESET_CONFIG" \
            --dynamic-delay-seconds 0 --dynamic-attack-enabled false
    else
        python3 attack/gps_hook.py --config "$PRESET_CONFIG"
    fi
fi

cat <<EOF

Done! SITL is running in the background (PID ${SITL_PID}, log: ${SITL_LOG}).

Next steps:
  1. Open QGroundControl: ./QGroundControl-x86_64.AppImage
  2. Plan view -> Open -> plans/${PRESET}.plan -> Upload
  3. Fly view -> Start Mission

When you're done, type 'kill' below to stop the simulation.
EOF

while true; do
    read -r -p "> " cmd
    if [[ "${cmd,,}" == "kill" ]]; then
        echo "Stopping simulation..."
        pkill -f 'build/sitl/bin/arducopter' || true
        pkill -f 'mavproxy.py.*5760' || true
        pkill -f 'xterm.*ArduCopter' || true
        sleep 2
        BIN_LOG=$(ls -t logs/*.BIN 2>/dev/null | head -1)
        if [[ -n "$BIN_LOG" ]]; then
            BIN_DEST="logs/${MODE}_${PRESET}.bin"
            cp "$BIN_LOG" "$BIN_DEST"
            echo "Saved flight log: ${BIN_DEST}"
        fi
        echo "Done."
        break
    fi
    echo "Type 'kill' to stop the simulation."
done

#!/bin/bash
# Usage: ./run_simulation.sh --attack-type {passthrough|static|dynamic|drift} --spawn-location {ornl|canberra}
set -euo pipefail

usage() {
    echo "Usage: $0 --attack-type {passthrough|static|dynamic|drift} --spawn-location {ornl|canberra}" >&2
    exit 1
}

ATTACK_TYPE=""
SPAWN_LOCATION=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --attack-type) ATTACK_TYPE="$2"; shift 2 ;;
        --spawn-location) SPAWN_LOCATION="$2"; shift 2 ;;
        *) echo "Unknown argument: $1" >&2; usage ;;
    esac
done

case "$ATTACK_TYPE" in
    passthrough|static|dynamic|drift) ;;
    *) echo "Invalid --attack-type: '$ATTACK_TYPE'" >&2; usage ;;
esac

case "$SPAWN_LOCATION" in
    ornl|canberra) ;;
    *) echo "Invalid --spawn-location: '$SPAWN_LOCATION'" >&2; usage ;;
esac

cd "$(dirname "$0")"

bash clear_persistent.sh
mkdir -p logs

read -r LAT LON ALT < <(python3 -c "
import yaml
coords = yaml.safe_load(open('plans/spawn_point_lookup.yaml'))['${SPAWN_LOCATION}']
print(coords['lat'], coords['lon'], coords['alt'])
")

SITL_LOG="logs/${ATTACK_TYPE}_${SPAWN_LOCATION}.log"
echo "Starting SITL (${SPAWN_LOCATION}) at ${LAT},${LON},${ALT}. Log: ${SITL_LOG}"
sim_vehicle.py -v ArduCopter \
    --custom-location="${LAT},${LON},${ALT},0" \
    --out udp:127.0.0.1:14550 \
    --out udp:127.0.0.1:14551 \
    > "$SITL_LOG" 2>&1 < <(tail -f /dev/null) &
SITL_PID=$!

cat <<EOF

SITL is starting (PID ${SITL_PID}, log: ${SITL_LOG}). While it initializes:
  1. Open QGroundControl: ./QGroundControl-x86_64.AppImage
  2. Plan view -> Open -> plans/${SPAWN_LOCATION}.plan -> Upload
  3. Fly view -> Start Mission when the simulation script says it's ready.

EOF

python3 simulation/run_simulation.py --attack-type "$ATTACK_TYPE" --spawn-location "$SPAWN_LOCATION"

echo ""
echo "Simulation complete. Type 'kill' to stop SITL and save the flight log."

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
            BIN_DEST="logs/${ATTACK_TYPE}_${SPAWN_LOCATION}.bin"
            cp "$BIN_LOG" "$BIN_DEST"
            echo "Saved flight log: ${BIN_DEST}"
        fi
        echo "Done."
        break
    fi
    echo "Type 'kill' to stop the simulation."
done

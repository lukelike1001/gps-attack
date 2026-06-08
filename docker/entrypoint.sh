#!/bin/bash
set -e

source /home/ardupilot/.ardupilot_env

exec /ardupilot/Tools/autotest/sim_vehicle.py \
    -v ArduCopter \
    --out "udp:host.docker.internal:${MAVLINK_GCS_PORT}" \
    --out "udp:127.0.0.1:${MAVLINK_SCRIPT_PORT}"

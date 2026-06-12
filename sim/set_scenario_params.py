"""
Load the ArduPilot SITL parameters for the GPS spoofing experiment.

Two modes:
  baseline:    enables the geofence and resets GPS to ArduPilot defaults
  attack:      enables the geofence and switches GPS to MAVLink input so
               GPS_INPUT messages are accepted (run once before the spoofed
               flight; injection itself is handled by attack/gps_hook.py)

Connects on the secondary MAVProxy UDP port (14551) to avoid conflicting
with QGroundControl, which listens on 14550.

All tunable values live in sim/scenario_params.yaml.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping
from pathlib import Path
from pymavlink import mavutil

from scenario_config import ScenarioConfig

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from communication.connect_to_sitl import ConnectionConfig, SitlConnection


class ScenarioLoader:
    """Sets and verifies ArduPilot parameters over MAVLink."""

    def __init__(self, connection: SitlConnection, scenario_config: ScenarioConfig) -> None:
        """Initialise with an active connection and injected configuration."""
        self._connection = connection
        self._scenario_config = scenario_config

    def set_parameter(self, name: str, value: float) -> bool:
        """Send a PARAM_SET message and confirm the ACK.

        Args:
            name: ArduPilot parameter name (e.g. "FENCE_ENABLE").
            value: Desired parameter value.

        Returns:
            True if the parameter was confirmed, False after all retries fail.
        """
        mav = self._connection.mav
        for attempt in range(1, self._scenario_config.max_retries + 1):
            mav.mav.param_set_send(
                mav.target_system,
                mav.target_component,
                name.encode("utf-8"),
                float(value),
                mavutil.mavlink.MAV_PARAM_TYPE_REAL32,
            )
            ack = mav.recv_match(
                type="PARAM_VALUE",
                blocking=True,
                timeout=self._scenario_config.ack_timeout_seconds,
            )
            if ack and ack.param_id.rstrip("\x00") == name:
                print(f"  {name:<24} = {value}")
                return True
            print(
                f"  {name}: no ACK "
                f"(attempt {attempt}/{self._scenario_config.max_retries})",
                flush=True,
            )
        print(f"  WARNING: could not confirm {name}")
        return False

    def apply_params(self, params: Mapping[str, float]) -> None:
        """Apply a mapping of parameter names to values.

        Args:
            params: Parameter name → value pairs to send to the flight controller.
        """
        for name, value in params.items():
            self.set_parameter(name, value)


def run(mode: str, reboot: bool) -> None:
    """Connect to the ArduPilot SITL and apply the parameter set for the requested mode.

    In attack mode the baseline params are applied first, then the attack-specific
    overrides are layered on top.

    Args:
        mode: Either "baseline" or "attack".
        reboot: If True, reboot SITL via MAVLink and wait for it to come back
            online so GPS1_TYPE changes take effect.
    """
    scenario_config = ScenarioConfig.from_yaml()
    connection_config = ConnectionConfig.from_yaml()

    scenario_params = (
        {**scenario_config.fence_params, **scenario_config.nav_params, **scenario_config.gps_baseline_params}
        if mode == "baseline"
        else {**scenario_config.fence_params, **scenario_config.nav_params, **scenario_config.gps_attack_params}
    )

    connection = SitlConnection(connection_config)
    connection.connect()

    scenario_loader = ScenarioLoader(connection, scenario_config)
    print(f"\nApplying {mode} parameters:")
    scenario_loader.apply_params(scenario_params)

    print(f"\nDone! {mode} parameters applied.")

    if reboot:
        print("\nRebooting SITL …")
        connection.reboot()
        print("SITL back online.")
    else:
        connection.close()
        print(
            "\nNOTE: Reboot the SITL (or send MAV_CMD_PREFLIGHT_REBOOT_SHUTDOWN) "
            "for GPS1_TYPE to take effect."
        )


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Set ArduPilot SITL parameters for GPS spoofing experiment"
    )
    parser.add_argument(
        "--mode",
        choices=["baseline", "attack"],
        default="baseline",
        help="Parameter set to apply (default: baseline)",
    )
    parser.add_argument(
        "--reboot",
        action="store_true",
        help="Reboot SITL via MAVLink and wait for it to come back online",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        run(args.mode, args.reboot)
    except (ConnectionError, FileNotFoundError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

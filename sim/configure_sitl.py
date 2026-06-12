"""
Configure ArduPilot SITL parameters for the GPS spoofing experiment.

Two modes:
  baseline:    enables the geofence and resets GPS to ArduPilot defaults
  attack:      enables the geofence and switches GPS to MAVLink input so
               GPS_INPUT messages are accepted (run once before the spoofed
               flight; injection itself is handled by attack/gps_hook.py)

Connects on the secondary MAVProxy UDP port (14551) to avoid conflicting
with QGroundControl, which listens on 14550.

All tunable values live in sim/sitl_params.yaml.
"""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

import yaml
from pymavlink import mavutil

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from communication.connect_to_sitl import ConnectionConfig, SitlConnection

CONFIG_PATH = Path(__file__).parent / "sitl_params.yaml"


@dataclass(frozen=True)
class Config:
    """Immutable runtime configuration loaded from sitl_params.yaml.

    Scalar fields are frozen by the dataclass. Parameter dicts are wrapped
    in MappingProxyType so their contents cannot be mutated after load.
    """

    param_ack_timeout_seconds: int
    param_max_retries: int
    fence_params: Mapping[str, float]
    nav_params: Mapping[str, float]
    gps_baseline_params: Mapping[str, float]
    gps_attack_params: Mapping[str, float]

    @classmethod
    def from_yaml(cls, path: Path = CONFIG_PATH) -> Config:
        """Load and validate configuration from a YAML file.

        Args:
            path: Path to the YAML config file.

        Raises:
            FileNotFoundError: If the config file does not exist.
            KeyError: If a required section or key is absent.
        """
        with path.open() as file:
            data = yaml.safe_load(file)
        return cls(
            param_ack_timeout_seconds=data["mavlink_params"]["ack_timeout_seconds"],
            param_max_retries=data["mavlink_params"]["max_retries"],
            fence_params=MappingProxyType(data["fence_params"]),
            nav_params=MappingProxyType(data["nav_params"]),
            gps_baseline_params=MappingProxyType(data["gps_baseline_params"]),
            gps_attack_params=MappingProxyType(data["gps_attack_params"]),
        )


class ParameterManager:
    """Sets and verifies ArduPilot parameters over MAVLink."""

    def __init__(self, connection: SitlConnection, config: Config) -> None:
        """Initialise with an active connection and injected configuration."""
        self._connection = connection
        self._config = config

    def set_parameter(self, name: str, value: float) -> bool:
        """Send a PARAM_SET message and confirm the ACK.

        Args:
            name: ArduPilot parameter name (e.g. "FENCE_ENABLE").
            value: Desired parameter value.

        Returns:
            True if the parameter was confirmed, False after all retries fail.
        """
        mav = self._connection.mav
        for attempt in range(1, self._config.param_max_retries + 1):
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
                timeout=self._config.param_ack_timeout_seconds,
            )
            if ack and ack.param_id.rstrip("\x00") == name:
                print(f"  {name:<24} = {value}")
                return True
            print(
                f"  {name}: no ACK "
                f"(attempt {attempt}/{self._config.param_max_retries})",
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


_REBOOT_SETTLE_SECONDS = 5


def reboot_and_wait(connection: SitlConnection, connection_config: ConnectionConfig) -> None:
    """Reboot SITL via MAVLink and block until it comes back online.

    Args:
        connection: An active connection to the SITL instance to reboot. Closed
            as part of the reboot.
        connection_config: Configuration used to reconnect once SITL restarts.

    Raises:
        ConnectionError: If SITL does not re-heartbeat within the configured timeout.
    """
    mav = connection.mav
    mav.mav.command_long_send(
        mav.target_system,
        mav.target_component,
        mavutil.mavlink.MAV_CMD_PREFLIGHT_REBOOT_SHUTDOWN,
        0,
        1, 0, 0, 0, 0, 0, 0,
    )
    connection.close()
    time.sleep(_REBOOT_SETTLE_SECONDS)

    new_connection = SitlConnection(connection_config)
    new_connection.connect()
    new_connection.close()


def run(mode: str, reboot: bool) -> None:
    """Connect to SITL and apply the parameter set for the requested mode.

    In attack mode the baseline params are applied first, then the attack-specific
    overrides are layered on top.

    Args:
        mode: Either "baseline" or "attack".
        reboot: If True, reboot SITL via MAVLink and wait for it to come back
            online so GPS1_TYPE changes take effect.
    """
    config = Config.from_yaml()
    connection_config = ConnectionConfig.from_yaml()

    params = (
        {**config.fence_params, **config.nav_params, **config.gps_baseline_params}
        if mode == "baseline"
        else {**config.fence_params, **config.nav_params, **config.gps_attack_params}
    )

    connection = SitlConnection(connection_config)
    connection.connect()

    manager = ParameterManager(connection, config)
    print(f"\nApplying {mode} parameters:")
    manager.apply_params(params)

    print(f"\nDone! {mode} parameters applied.")

    if reboot:
        print("\nRebooting SITL …")
        reboot_and_wait(connection, connection_config)
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

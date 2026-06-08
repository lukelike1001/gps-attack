"""
Configure ArduPilot SITL parameters for the GPS spoofing experiment.

Two modes:
  baseline  — geofence on, internal GPS (run before the clean flight)
  attack    — geofence on plus GPS1_TYPE=14 and EK3 tuning so MAVLink
               GPS_INPUT messages are accepted (run once before the spoofed
               flight; injection itself is handled by attack/gps_hook.py)

Connects on the secondary MAVProxy UDP port (14551) to avoid conflicting
with QGroundControl, which listens on 14550.

All tunable values live in mission/config.yaml.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

import yaml
from pymavlink import mavutil

CONFIG_PATH = Path(__file__).parent / "sitl_params.yaml"


@dataclass(frozen=True)
class Config:
    """Immutable runtime configuration loaded from config.yaml.

    Scalar fields are frozen by the dataclass. Parameter dicts are wrapped
    in MappingProxyType so their contents cannot be mutated after load.
    """

    connection_address: str
    heartbeat_timeout_seconds: int
    param_ack_timeout_seconds: int
    param_max_retries: int
    baseline_params: Mapping[str, float]
    attack_params: Mapping[str, float]

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
            connection_address=data["connection"]["address"],
            heartbeat_timeout_seconds=data["connection"]["heartbeat_timeout_seconds"],
            param_ack_timeout_seconds=data["parameters"]["ack_timeout_seconds"],
            param_max_retries=data["parameters"]["max_retries"],
            baseline_params=MappingProxyType(data["baseline_params"]),
            attack_params=MappingProxyType(data["attack_params"]),
        )


class SitlConnection:
    """Manages a MAVLink connection to ArduPilot SITL."""

    def __init__(self, config: Config) -> None:
        """Initialise with injected configuration; does not connect immediately."""
        self._config = config
        self._mav = None

    def connect(self) -> None:
        """Open the MAVLink connection and block until a heartbeat is received.

        Raises:
            ConnectionError: If no heartbeat arrives within the configured timeout.
        """
        print(f"Connecting to SITL at {self._config.connection_address} …", flush=True)
        self._mav = mavutil.mavlink_connection(self._config.connection_address)
        if not self._mav.wait_heartbeat(timeout=self._config.heartbeat_timeout_seconds):
            raise ConnectionError(
                f"No heartbeat from SITL within "
                f"{self._config.heartbeat_timeout_seconds}s. "
                "Is sim_vehicle.py running?"
            )
        print(
            f"  system {self._mav.target_system} "
            f"component {self._mav.target_component} online"
        )

    def close(self) -> None:
        """Close the MAVLink connection if one is open."""
        if self._mav:
            self._mav.close()

    @property
    def mav(self):
        """Return the active MAVLink handle.

        Raises:
            RuntimeError: If called before connect().
        """
        if not self._mav:
            raise RuntimeError("Call connect() before accessing the MAVLink handle.")
        return self._mav


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


def run(mode: str) -> None:
    """Connect to SITL and apply the parameter set for the requested mode.

    In attack mode the baseline params are applied first, then the attack-specific
    overrides are layered on top.

    Args:
        mode: Either "baseline" or "attack".
    """
    config = Config.from_yaml()

    params = (
        config.baseline_params
        if mode == "baseline"
        else {**config.baseline_params, **config.attack_params}
    )

    connection = SitlConnection(config)
    connection.connect()

    manager = ParameterManager(connection, config)
    print(f"\nApplying {mode} parameters:")
    manager.apply_params(params)

    connection.close()
    print(f"\nDone — {mode} parameters applied.")

    if mode == "attack":
        print(
            "\nNOTE: Reboot the SITL (or send MAV_CMD_PREFLIGHT_REBOOT_SHUTDOWN) "
            "for GPS1_TYPE and EK3_GPS_TYPE to take effect."
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
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        run(args.mode)
    except (ConnectionError, FileNotFoundError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

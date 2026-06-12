"""
Manage a MAVLink connection to ArduPilot SITL.

Shared by sim/set_scenario_params.py and attack/gps_hook.py: both connect on the
secondary MAVProxy UDP port (14551) to avoid conflicting with QGroundControl,
which listens on 14550.

All tunable values live in communication/connect_to_sitl_params.yaml.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import yaml
from pymavlink import mavutil

CONFIG_PATH = Path(__file__).parent / "connect_to_sitl_params.yaml"


@dataclass(frozen=True)
class ConnectionConfig:
    """Immutable connection settings loaded from connect_to_sitl_params.yaml."""

    connection_address: str
    heartbeat_timeout_seconds: int
    reboot_settle_seconds: int

    @classmethod
    def from_yaml(cls, path: Path = CONFIG_PATH) -> ConnectionConfig:
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
            connection_address=data["connection_params"]["address"],
            heartbeat_timeout_seconds=data["connection_params"]["heartbeat_timeout_seconds"],
            reboot_settle_seconds=data["connection_params"]["reboot_settle_seconds"],
        )


class SitlConnection:
    """Manages a MAVLink connection to ArduPilot SITL."""

    def __init__(self, config: ConnectionConfig) -> None:
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
    
    def reboot(self) -> None:
        """Reboot SITL via MAVLink and block until it comes back online.

        Closes the current connection as part of the reboot until the connection
        automatically re-establishes itself. We also open and close a separate,
        temporary connection to confirm that the SITL has come back online.

        This function is the equivalent of typing `reboot` directly into the MAVLink
        terminal, but used for automation without user input such as the master script.

        Raises:
            ConnectionError: If SITL does not re-heartbeat within the configured timeout.
        """
        mav = self.mav
        mav.mav.command_long_send(
            mav.target_system,
            mav.target_component,
            mavutil.mavlink.MAV_CMD_PREFLIGHT_REBOOT_SHUTDOWN,
            0,
            1, 0, 0, 0, 0, 0, 0,
        )

        self.close()
        print("ArduPilot will automatically attempt to reconnect to MAVLink...")
        time.sleep(self._config.reboot_settle_seconds)
        self.verify_successful_reboot()
        print("Reconnected successfully!")
    
    def verify_successful_reboot(self) -> None:
        """Verify that the SITL connection has come back online.

        Raises:
            ConnectionError: If SITL does not re-heartbeat within the configured timeout.
        """
        temporary_check_connection = SitlConnection(self._config)
        temporary_check_connection.connect()
        temporary_check_connection.close()

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

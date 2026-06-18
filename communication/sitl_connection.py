"""
Manage a MAVLink connection to ArduPilot SITL.

Connects the drone, flight environment, and the SDR to the secondary MAVProxy
UDP port (14551) to avoid conflicting with QGroundControl, which listens on 14550.

All tunable values live in communication/sitl_connection_params.yaml.
"""

import time
from pymavlink import mavutil

from .sitl_connection_config import ConnectionConfig

class SitlConnection:
    """Manages a MAVLink connection to ArduPilot SITL."""

    def __init__(self, config: ConnectionConfig) -> None:
        """Initialise with injected configuration; does not connect immediately."""
        self.config = config
        self.mav = None
        

    def connect(self) -> None:
        """Open the MAVLink connection and block until a heartbeat is received.

        Raises:
            ConnectionError: If no heartbeat arrives within the configured timeout.
        """
        print(f"Connecting to SITL at {self.config.connection_address} …", flush=True)
        self.mav = mavutil.mavlink_connection(self.config.connection_address)
        if not self.mav.wait_heartbeat(timeout=self.config.heartbeat_timeout_seconds):
            raise ConnectionError(
                f"No heartbeat from SITL within "
                f"{self.config.heartbeat_timeout_seconds}s. "
                "Is sim_vehicle.py running?"
            )
        print(
            f"  system {self.mav.target_system} "
            f"component {self.mav.target_component} online"
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
        time.sleep(self.config.reboot_settle_seconds)
        self.verify_successful_reboot()
        print("Reconnected successfully!")
    

    def verify_successful_reboot(self) -> None:
        """Verify that the SITL connection has come back online.

        Raises:
            ConnectionError: If SITL does not re-heartbeat within the configured timeout.
        """
        temporary_check_connection = SitlConnection(self.config)
        temporary_check_connection.connect()
        temporary_check_connection.close()


    def close(self) -> None:
        """Close the MAVLink connection if one is open."""
        if self.mav:
            self.mav.close()


    @property
    def mav(self):
        """Return the active MAVLink handle.

        Raises:
            RuntimeError: If called before connect().
        """
        if not self.mav:
            raise RuntimeError("Call connect() before accessing the MAVLink handle.")
        return self.mav

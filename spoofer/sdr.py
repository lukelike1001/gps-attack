from attack.gps_attack import GpsAttack
from communication.sitl_connection import SitlConnection
from drone.gps_receiver import GpsReceiver
from spoofer.sdr_config import SdrConfig
import time

class SoftwareDefinedRadio:

    def __init__(self, gps_attack: GpsAttack):
        self.config = SdrConfig.from_yaml()
        self.attack = gps_attack
    

    def activate_gps_attack(self, gps_receiver: GpsReceiver, connection: SitlConnection) -> None:
        """Run a GPS spoofing attack for the specified duration as defined in `self.config.attack_duration_seconds`
        Only called by GpsSpoofingSimulation after the `Drone`, `FlightEnvironment`, and the `SitlConnection have
        already been established."""

        start_time = time.monotonic()
        elapsed_seconds = 0.0
        interval_seconds = 1.0 / self.config.gps_input_rate_hz

        while elapsed_seconds < self.config.attack_duration_seconds:
            elapsed_seconds = time.monotonic() - start_time
            spoofed_position = self.attack.compute_spoofed_position(gps_receiver, elapsed_seconds)
            spoofed_velocity = self.attack.compute_spoofed_velocity(gps_receiver, elapsed_seconds)
            self.send_gps_input(gps_receiver, spoofed_position, spoofed_velocity, connection)
            time.sleep(interval_seconds)

            # NOTE: time.sleep accumulates drift over time because it doesn't account for how long
            # send_gps_input took, and should be modified for future tests
    

    def send_gps_input(self,
        gps_receiver: GpsReceiver,
        spoofed_position: tuple[float, float, float],
        spoofed_velocity: tuple[float, float, float],
        connection: SitlConnection
    ) -> None:
        """Send a single spoofed GPS_INPUT message using the spoofed position and velocity
        calculated from the GpsAttack call in `activate_gps_attack()`"""
        spoofed_lat, spoofed_lon, spoofed_alt = spoofed_position
        spoofed_velocity_north, spoofed_velocity_east, spoofed_velocity_down = spoofed_velocity

        # NOTE: We can make later edits to modify the GPS to support spoofed time
        # in addition to just position and velocity
        seconds_since_gps_epoch = time.time() - self.config.gps_epoch_unix
        gps_week, seconds_into_week = divmod(seconds_since_gps_epoch, self.config.seconds_per_week)
        signal_quality_params = gps_receiver.get_signal_quality_params()

        # NOTE: I should externalize these random magic values (low priority)
        # NOTE: In the real world, mav.gps_input_send isn't the most accurate way to simulate them.
        # In the real world, spoofers use 
        connection.mav.mav.gps_input_send(
            int(time.time() * 1e6),         # time_usec
            0,                              # gps_id
            0,                              # ignore_flags because every field below is valid
            int(seconds_into_week * 1000),  # time_week_ms
            int(gps_week),                  # time_week
            signal_quality_params["fix_type_3d"],              # fix_type
            int(spoofed_lat * 1e7),             # lat, degE7
            int(spoofed_lon * 1e7),             # lon, degE7
            spoofed_alt,                        # alt, m MSL
            signal_quality_params["hdop"],
            signal_quality_params["vdop"],
            spoofed_velocity_north,
            spoofed_velocity_east,
            spoofed_velocity_down,
            signal_quality_params["speed_accuracy"],
            signal_quality_params["horizontal_accuracy"],
            signal_quality_params["vertical_accuracy"],
            signal_quality_params["satellites_visible_count"],
            0,                          # yaw, 0 = unknown
        )

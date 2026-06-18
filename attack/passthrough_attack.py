from attack.gps_attack import GpsAttack
from pathlib import Path
from drone.gps_receiver import GpsReceiver

class PassthroughAttack(GpsAttack):
    ATTACK_TYPE = "passthrough"

    def compute_spoofed_position(
            self, gps_receiver: GpsReceiver, elapsed_seconds: float
    ) -> tuple[float, float, float]:
        """Given a drone and the elapsed time, return the coordinates without any spoofing."""
        return (gps_receiver.lat, gps_receiver.lon, gps_receiver.alt)
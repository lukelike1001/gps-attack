from attack.gps_attack import GpsAttack
from pathlib import Path
from drone.gps_receiver import GpsReceiver

class DriftAttack(GpsAttack):
    ATTACK_TYPE = "drift"

    def __init__(self, config_path: Path):
        self._from_yaml(config_path)
        self._verify_attack_type()
        self.drift_rate_lat = self.config["drift_rate_lat"]
        self.drift_rate_lon = self.config["drift_rate_lon"]

    def compute_spoofed_position(
            self, gps_receiver: GpsReceiver, elapsed_seconds: float
    ) -> tuple[float, float, float]:
        """Given a drone and the elapsed time, calculate the new spoofed location."""
        
        return (
            gps_receiver.lat + self.drift_rate_lat * elapsed_seconds,
            gps_receiver.lon + self.drift_rate_lon * elapsed_seconds,
            gps_receiver.alt,
        )
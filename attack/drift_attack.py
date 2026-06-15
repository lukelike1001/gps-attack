from attack.gps_attack import GpsAttack
from pathlib import Path
from sim.drone import Drone

class DriftAttack(GpsAttack):
    ATTACK_TYPE = "drift"

    def __init__(self, config_path: Path):
        self._load_yaml(config_path)
        self._verify_attack_type()
        self.drift_rate_lat = self.config["drift_rate_lat"]
        self.drift_rate_lon = self.config["drift_rate_lon"]

    def compute_spoofed_position(
            self, drone: Drone, elapsed_seconds: float
    ) -> tuple[float, float, float]:
        """Given a drone and the elapsed time, calculate the new spoofed location."""
        
        return (
            drone.lat + self.drift_rate_lat * elapsed_seconds,
            drone.lon + self.drift_rate_lon * elapsed_seconds,
            drone.alt,
        )
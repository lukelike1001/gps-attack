from attack.fabric_attack import FabricAttack
from pathlib import Path
from drone.gps_receiver import GpsReceiver

class StaticAttack(FabricAttack):
    ATTACK_TYPE = "static"

    def __init__(self, config_path: Path):
        super().__init__(config_path)

    def compute_spoofed_position(
            self, gps_receiver: GpsReceiver, elapsed_seconds: float
    ) -> tuple[float, float, float]:
        """Given a drone and the elapsed time, calculate the new spoofed location."""
        return (self.fabric_lat, self.fabric_lon, self.fabric_alt)

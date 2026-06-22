from attack.fabric_attack import FabricAttack
from drone.gps_receiver import GpsReceiver

class StaticAttack(FabricAttack):
    ATTACK_TYPE = "static"

    def __init__(self, attack_type: str, spawn_location: str):
        super().__init__(attack_type, spawn_location)

    def compute_spoofed_position(
            self, gps_receiver: GpsReceiver, elapsed_seconds: float
    ) -> tuple[float, float, float]:
        """Given a drone and the elapsed time, calculate the new spoofed location."""
        return (self.fabric_lat, self.fabric_lon, self.fabric_alt)
    
    
    def compute_spoofed_velocity(
            self, gps_receiver: GpsReceiver, elapsed_seconds: float
    ) -> tuple[float, float, float]:
        """The static attack does not affect the drone's velocity"""
        return gps_receiver.get_velocity()

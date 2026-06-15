from attack.gps_attack import GpsAttack
from pathlib import Path
from sim.drone import Drone

class PassthroughAttack(GpsAttack):

    def compute_spoofed_position(
            self, drone: Drone, elapsed_seconds: float
    ) -> tuple[float, float, float]:
        """Given a drone and the elapsed time, return the coordinates without any spoofing."""
        return (drone.lat, drone.lon, drone.alt)
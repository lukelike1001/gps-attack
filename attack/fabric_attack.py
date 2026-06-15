from attack.gps_attack import GpsAttack
from pathlib import Path
from sim.drone import Drone

class FabricAttack(GpsAttack):

    def __init__(self, config_path: Path):
        self._load_yaml(config_path)
        self._verify_attack_type()
        self.fabric_lat = self.config["fabric_lat"]
        self.fabric_lon = self.config["fabric_lon"]
        self.fabric_alt = self.config["fabric_alt"]
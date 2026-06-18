from attack.gps_attack import GpsAttack
from pathlib import Path
from drone.gps_receiver import GpsReceiver

class FabricAttack(GpsAttack):
    # this is an abstract class that you should NOT call

    def __init__(self, config_path: Path):
        self._from_yaml(config_path)
        self._verify_attack_type()
        self.fabric_lat = self.config["fabric_lat"]
        self.fabric_lon = self.config["fabric_lon"]
        self.fabric_alt = self.config["fabric_alt"]
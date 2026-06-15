from attack.fabric_attack import FabricAttack
from pathlib import Path
from sim.drone import Drone

class DynamicAttack(FabricAttack):

    def __init__(self, config_path: Path):
        super().__init__(config_path)
        self.dynamic_attack_alt = self.config["dynamic_attack_alt"]
        self.dynamic_delay_seconds = self.config["dynamic_delay_seconds"]

    def compute_spoofed_position(
            self, drone: Drone, elapsed_seconds: float
    ) -> tuple[float, float, float]:
        """Given a drone and the elapsed time, calculate the new spoofed location."""
        
        # we need to still implement stuff here
        # conceptually, we first check if the drone reached the altitude defined in `self.dynamic_attack_alt`
        # after `self.dynamic_delay_seconds` have passed after first reaching the attack alt, start the dynamic spoof

        pass

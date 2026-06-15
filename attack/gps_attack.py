from __future__ import annotations

from abc import ABC, abstractmethod
from sim.drone import Drone
from pathlib import Path
import yaml

class GpsAttack(ABC):
    """Abstract GPS spoofing attack class intended for extension"""
    config = None

    def _verify_attack_type(self) -> None:
        provided_attack = self.config["type"]
        expected_attack = self.ATTACK_TYPE
        if provided_attack != expected_attack:
            raise ValueError(f"The YAML config defines a {provided_attack}, but the class expects {expected_attack} parameters.")

    def _load_yaml(self, config_path: Path) -> None:
        """Open a YAML config file and return the raw data"""
        with config_path.open() as file:
            attack_config = yaml.safe_load(file)
        self.config = attack_config

    @abstractmethod
    def compute_spoofed_position(self, drone: Drone, elapsed_seconds: float
    ) -> tuple[float, float, float]:
        """Given a drone and the elapsed time, calculate the new spoofed location."""
        pass
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).parent / "sdr_params.yaml"

@dataclass(frozen=True)
class SdrConfig:
    """Immutable SDR settings loaded from sdr_params.yaml."""

    gps_input_rate_hz: float
    attack_duration_seconds: float
    gps_epoch_unix: int
    seconds_per_week: int

    @classmethod
    def from_yaml(cls, path: Path = CONFIG_PATH) -> SdrConfig:
        """Load and validate configuration from a YAML file.

        Args:
            path: Path to the YAML config file.

        Raises:
            FileNotFoundError: If the config file does not exist.
            KeyError: If a required section or key is absent.
        """
        with path.open() as file:
            data = yaml.safe_load(file)
        return cls(
            gps_input_rate_hz=data["gps_input_rate_hz"],
            attack_duration_seconds=data["attack_duration_seconds"],
            gps_epoch_unix=data["gps_epoch_unix"],
            seconds_per_week=data["seconds_per_week"]
        )

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

import yaml

SCENARIO_CONFIG_PATH = Path(__file__).parent / "scenario_params.yaml"

@dataclass(frozen=True)
class ScenarioConfig:
    """Immutable runtime configuration loaded from scenario_params.yaml.

    Scalar fields are frozen by the dataclass. Parameter dicts are wrapped
    in MappingProxyType so their contents cannot be mutated after load.
    """

    ack_timeout_seconds: int
    max_retries: int
    fence_params: Mapping[str, float]
    nav_params: Mapping[str, float]
    gps_baseline_params: Mapping[str, float]
    gps_attack_params: Mapping[str, float]

    @classmethod
    def from_yaml(cls, path: Path = SCENARIO_CONFIG_PATH) -> ScenarioConfig:
        """Load and validate configuration from a YAML file.

        Args:
            path: Path to the YAML cscenario onfig file.

        Raises:
            FileNotFoundError: If the scenario config file does not exist.
            KeyError: If a required section or key is absent.
        """
        with path.open() as file:
            data = yaml.safe_load(file)
        return cls(
            ack_timeout_seconds=data["mavlink_params"]["ack_timeout_seconds"],
            max_retries=data["mavlink_params"]["max_retries"],
            fence_params=MappingProxyType(data["fence_params"]),
            nav_params=MappingProxyType(data["nav_params"]),
            gps_baseline_params=MappingProxyType(data["gps_baseline_params"]),
            gps_attack_params=MappingProxyType(data["gps_attack_params"]),
        )
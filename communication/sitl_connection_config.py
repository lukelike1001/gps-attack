from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

import yaml

CONFIG_PATH = Path(__file__).parent / "sitl_connection_params.yaml"

@dataclass(frozen=True)
class ConnectionConfig:
    """Immutable connection settings loaded from sitl_connection_params.yaml."""

    address: str
    heartbeat_timeout_seconds: int
    reboot_settle_seconds: int
    ack_timeout_seconds: int
    max_retries: int
    fence_params: Mapping[str, float]
    nav_params: Mapping[str, float]
    gps_passthrough_params: Mapping[str, float]
    gps_attack_params: Mapping[str, float]

    @classmethod
    def from_yaml(cls, path: Path = CONFIG_PATH) -> ConnectionConfig:
        """Load and validate configuration from a YAML file.

        Raises:
            FileNotFoundError: If the config file does not exist.
            KeyError: If a required section or key is absent.
        """
        with path.open() as file:
            data = yaml.safe_load(file)
        conn = data["connection_params"]
        return cls(
            address=conn["address"],
            heartbeat_timeout_seconds=conn["heartbeat_timeout_seconds"],
            reboot_settle_seconds=conn["reboot_settle_seconds"],
            ack_timeout_seconds=conn["ack_timeout_seconds"],
            max_retries=conn["max_retries"],
            fence_params=MappingProxyType(data["fence_params"]),
            nav_params=MappingProxyType(data["nav_params"]),
            gps_passthrough_params=MappingProxyType(data["gps_passthrough_params"]),
            gps_attack_params=MappingProxyType(data["gps_attack_params"]),
        )

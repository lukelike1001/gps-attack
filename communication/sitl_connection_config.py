from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import yaml

CONFIG_PATH = Path(__file__).parent / "sitl_connection_params.yaml"

@dataclass(frozen=True)
class ConnectionConfig:
    """Immutable connection settings loaded from sitl_connection_params.yaml."""

    connection_address: str
    heartbeat_timeout_seconds: int
    reboot_settle_seconds: int

    @classmethod
    def from_yaml(cls, path: Path = CONFIG_PATH) -> ConnectionConfig:
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
            connection_address=data["address"],
            heartbeat_timeout_seconds=data["heartbeat_timeout_seconds"],
            reboot_settle_seconds=data["reboot_settle_seconds"],
        )
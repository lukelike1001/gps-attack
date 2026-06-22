from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path
import yaml

from communication.sitl_connection_config import ConnectionConfig
from communication.sitl_connection import SitlConnection
from drone.drone import Drone
from spoofer.sdr import SoftwareDefinedRadio

SPAWN_LOOKUP_PATH = "plans/spawn_point_lookup.yaml"

class GpsSpoofingSimulation:

    connection: SitlConnection
    drone: Drone
    sdr: SoftwareDefinedRadio

    def __init__(self):
        pass


    def _instantiate_attack(self, attack_type: str, spawn_location: str):
        module = importlib.import_module(f"attack.{attack_type}_attack")
        cls = getattr(module, f"{attack_type.capitalize()}Attack")
        return cls(attack_type, spawn_location)


    def initialize_spoofing_simulation_components(self, attack_type: str, spawn_location: str):
        connection_config = ConnectionConfig.from_yaml()
        self.connection = SitlConnection(connection_config)
        self.drone = Drone()
        gps_attack = self._instantiate_attack(attack_type, spawn_location)
        self.sdr = SoftwareDefinedRadio(gps_attack)

    
    def find_spawn_coordinates(self, spawn_location: str):
        lookup_path = Path(SPAWN_LOOKUP_PATH)
        with lookup_path.open() as f:
            spawn_data = yaml.safe_load(f)
        spawn_coordinates = spawn_data[spawn_location]
        return (spawn_coordinates["lat"], spawn_coordinates["lon"], spawn_coordinates["alt"])
    

    def configure_ardupilot_connection(self, attack_type: str):
        print("Connecting to ArduPilot SITL...")
        self.connection.connect()
        self.connection.set_all_ardupilot_parameters(attack_type)
        print("Rebooting ArduPilot SITL...")
        self.connection.reboot()
        print("Sucessfully rebooted!")


    def run_spoofing_simulation(self, attack_type: str, spawn_location: str):
        self.initialize_spoofing_simulation_components(attack_type, spawn_location)
        self.configure_ardupilot_connection(attack_type)

        gps_receiver = self.drone.get_gps_receiver()
        spawn_lat, spawn_lon, spawn_alt = self.find_spawn_coordinates(spawn_location)
        gps_receiver.update_position(spawn_lat, spawn_lon, spawn_alt)
        gps_receiver.update_velocity(0.0, 0.0, 0.0)

        print("Activating GPS Spoofing Attack...")
        self.sdr.activate_gps_attack(gps_receiver, self.connection)
        print("Log results here - Placeholder!")
        self.connection.close()
    

    @staticmethod
    def parse_args() -> argparse.Namespace:
        """Parse command-line arguments."""
        parser = argparse.ArgumentParser(
            description="Set ArduPilot SITL parameters for GPS spoofing experiment"
        )
        parser.add_argument(
            "--attack-type",
            choices=["passthrough", "static", "dynamic", "drift"],
            default="passthrough",
            help="GPS attack type to apply (default: passthrough, no attack)",
        )
        parser.add_argument(
            "--spawn-location",
            choices=["ornl", "canberra"],
            default="ornl",
            help="Preset that loads the initial spawn location for the drone",
        )
        return parser.parse_args()
    

if __name__ == "__main__":
    simulation = GpsSpoofingSimulation()
    args = simulation.parse_args()
    try:
        simulation.run_spoofing_simulation(args.attack_type, args.spawn_location)
    except (ConnectionError, FileNotFoundError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

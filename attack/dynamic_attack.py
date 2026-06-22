from attack.fabric_attack import FabricAttack
from drone.gps_receiver import GpsReceiver
import math

import sys

class DynamicAttack(FabricAttack):
    ATTACK_TYPE = "dynamic"

    def __init__(self, attack_type: str, spawn_location: str):
        super().__init__(attack_type, spawn_location)
        self.dynamic_attack_alt = self.config["dynamic_attack_alt"]
        self.dynamic_attack_alt_tolerance = self.config["dynamic_attack_alt_tolerance"]
        self.dynamic_delay_seconds = self.config["dynamic_delay_seconds"]
        self.reached_time = math.inf
    

    def compute_spoofed_position(
            self, gps_receiver: GpsReceiver, elapsed_seconds: float
    ) -> tuple[float, float, float]:
        """Given a drone and the elapsed time, calculate the new spoofed location."""
        drone_lat, drone_lon, drone_alt = gps_receiver.get_position()
        
        if abs(drone_alt - self.dynamic_attack_alt) < self.dynamic_attack_alt_tolerance:
            if self.reached_time == math.inf:
                print(f"Attack activated! Dynamic coordinates will display in {self.dynamic_delay_seconds} seconds.")
                self.reached_time = elapsed_seconds
        
        if elapsed_seconds - self.reached_time > self.dynamic_delay_seconds:
            return (self.fabric_lat, self.fabric_lon, self.fabric_alt)
        else:
            return gps_receiver.get_position()
        
    
    def compute_spoofed_velocity(
            self, gps_receiver: GpsReceiver, elapsed_seconds: float
    ) -> tuple[float, float, float]:
        """By definition, passthrough does not affect the drone's velocity"""
        return gps_receiver.get_velocity()

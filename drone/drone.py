from drone.compass import Compass
from drone.imu import InertialMeasurementUnit
from drone.gps_receiver import GpsReceiver

class Drone:

    def __init__(self):
        """
        Purpose: Initialize the drone's hardware components.

        Note: These aren't real hardware parts, but rather software
        representations of them.
        """
        self.compass = Compass()
        self.imu = InertialMeasurementUnit()
        self.gps_receiver = GpsReceiver()
        pass


    def get_gps_receiver(self):
        """Getter method for the drone's GPS receiver"""
        return self.gps_receiver
    
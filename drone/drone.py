from drone.compass import Compass
from drone.imu import InertialMeasurementUnit
from drone.gps_receiver import GpsReceiver

class Drone:

    def __init__(self, compass: Compass, imu: InertialMeasurementUnit,
                 gps_receiver: GpsReceiver):
        self.compass = compass
        self.imu = imu
        self.gps_receiver = gps_receiver
        pass

    def set_performance_specifications(self):
        # we set the ascent rate, descent rate, and so on...
        pass
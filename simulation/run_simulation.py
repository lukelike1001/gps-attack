from communication.sitl_connection import SitlConnection
from drone.drone import Drone
from environment.flight_environment import FlightEnvironment
from spoofer.sdr import SoftwareDefinedRadio

class GpsSpoofingSimulation:
    """
    Tentative Plan: (remove this comment when ready to commit)

    Step 1: Create an `SitlConnection` that opens pre-configured ports
    Step 2: Create the drone using the `Drone` class, which comes with
            the Compass, IMU, and the Drone
    Step 3: Create the `FlightEnvironment` (using the `.plan` file)
    Step 4: Create the `SoftwareDefinedRadio`, which comes with the
            pre-defined `GpsAttack` (configurable and abstracted)
    Step 5: Activate the GPS attack and coordinate with QGroundControl
    Step 6: Record telemetry logs
    """

    connection: SitlConnection
    drone: Drone
    environment: FlightEnvironment
    sdr: SoftwareDefinedRadio

    def __init__(self):
        self.connection = SitlConnection() # need to add a config
        self.drone = Drone() # need config here too
        self.environment = FlightEnvironment() # need config here too
        self.sdr = SoftwareDefinedRadio() # need config here too

        # Steps 1-4 run in the __init__

    def run_spoofing_simulation(self):
        self.sdr.activate_gps_attack(self.drone.gps_receiver, self.connection) # <-- This is Step 5
        print("Log results here") # <-- This is Step 6 (placeholder)
        return # (finished running by here)
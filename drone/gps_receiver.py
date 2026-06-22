from communication.sitl_connection import SitlConnection
from pathlib import Path
import yaml

import sys

GPS_RECEIVER_CONFIG_PATH = Path(__file__).parent / "configs" / "gps_receiver_params.yaml"

class GpsReceiver:
    """Software representation of the drone's GPS receiver, which stores
    its position and velocity value read from GLOBAL_POSITION_INT.

    Velocity is in the NED frame (m/s), matching GPS_INPUT's vn/ve/vd fields.
    `alt` is height above mean sea level
    """

    lat: float
    lon: float
    alt: float
    velocity_north: float
    velocity_east: float
    velocity_down: float

    def __init__(self, config_path: Path = GPS_RECEIVER_CONFIG_PATH):
        """Initialization the normalization constants and the initial position/velocity"""
        self._from_yaml(config_path)
        # NOTE: insert another line that polls for the initial position and velocity
        pass


    def _from_yaml(self, config_path: Path) -> None:
        """Load the config from YAML and store the signal and """
        with config_path.open() as file:
            data = yaml.safe_load(file)
        self.signal_quality_params = data["signal_quality_params"]
        self.norms = data["norm_params"]


    def update_position(self, new_lat: float, new_lon: float, new_alt: float):
        """Helper method that updates the drone's new position"""
        self.lat = new_lat
        self.lon = new_lon
        self.alt = new_alt


    def update_velocity(self, new_velocity_north: float,
                        new_velocity_east: float, new_velocity_down: float):
        """Helper method that updates the drone's new NED velocity"""
        self.velocity_north = new_velocity_north
        self.velocity_east = new_velocity_east
        self.velocity_down = new_velocity_down


    def get_position(self):
        """Returns the drone's current position"""
        return (self.lat, self.lon, self.alt)
    

    def get_velocity(self):
        """Returns the drone's current velocity NED (north, east, down)"""
        return (self.velocity_north, self.velocity_east, self.velocity_down)
    

    def normalize_position(self, lat: float, lon: float, alt: float) -> tuple[float, float, float]:
        """Normalize the position based on pre-set normalization factors"""
        norm_lat = lat / self.norms["lat_factor"]
        norm_lon = lon / self.norms["lon_factor"]
        norm_alt = alt / self.norms["alt_factor"]
        return (norm_lat, norm_lon, norm_alt)
    
    
    def normalize_velocity(self, vx: float, vy: float, vz: float) -> tuple[float, float, float]:
        """Normalize the velocities based on pre-set normalization factors"""
        norm_vx = vx / self.norms["vx_factor"]
        norm_vy = vy / self.norms["vy_factor"]
        norm_vz = vz / self.norms["vz_factor"]
        return (norm_vx, norm_vy, norm_vz)
    
    
    def sync_position_and_velocity_to_sitl(self, connection: SitlConnection):
        """Poll for a fresh GLOBAL_POSITION_INT to update the drone's position and velocity"""
        msg = connection.mav.recv_match(type="GLOBAL_POSITION_INT", blocking=False)
        
        if msg is None:
            return None
        
        # IMPORTANT: Don't remove this "Null Island" fix.
        if msg.lat == 0 and msg.lon == 0:
            # "Null Island": the EKF hasn't ingested a GPS fix yet and has
            # no origin set, so GLOBAL_POSITION_INT reports (0, 0).
            return None

        norm_lat, norm_lon, norm_alt = self.normalize_position(msg.lat, msg.lon, msg.alt)
        norm_vx, norm_vy, norm_vz = self.normalize_velocity(msg.vx, msg.vy, msg.vz)
        
        self.update_position(norm_lat, norm_lon, norm_alt)
        self.update_velocity(norm_vx, norm_vy, norm_vz)
    

    def get_signal_quality_params(self):
        """Returns the signal quality params used for sending GPS input messages via MAVLink.
        
        MAJOR DISCLAIMER: In a real-world GPS spoofing attack, the GPS doesn't ask the drone's
        GPS receiver for values like the HDOP, vertical accuracy, and so on. However, to
        simplify the simulation's design before expanding the complexity, we will use this
        shortcut for now. A real spoof would use an ephemeris file and simulate the satellites.
        """
        return self.signal_quality_params
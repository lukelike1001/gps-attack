import pytest
from unittest.mock import MagicMock

from attack.drift_attack import DriftAttack


@pytest.fixture
def drift_attack():
    return DriftAttack("drift", "ornl")


@pytest.fixture
def receiver():
    r = MagicMock()
    r.lat = 35.9305
    r.lon = -84.3107
    r.alt = 50.0
    r.get_velocity.return_value = (1.0, 2.0, -0.5)
    return r


class TestDriftAttack:

    def test_load_nonexistent_spawn_location_raises_key_error(self):
        with pytest.raises(KeyError):
            DriftAttack("drift", "paris")

    def test_compute_spoofed_position_applies_drift_rates(self, drift_attack, receiver):
        elapsed = 10.0
        lat, lon, alt = drift_attack.compute_spoofed_position(receiver, elapsed)
        assert lat == pytest.approx(receiver.lat + drift_attack.drift_rate_lat * elapsed)
        assert lon == pytest.approx(receiver.lon + drift_attack.drift_rate_lon * elapsed)
        assert alt == receiver.alt

    def test_compute_spoofed_velocity_returns_receiver_velocity_unchanged(self, drift_attack, receiver):
        result = drift_attack.compute_spoofed_velocity(receiver, elapsed_seconds=10.0)
        assert result == receiver.get_velocity()

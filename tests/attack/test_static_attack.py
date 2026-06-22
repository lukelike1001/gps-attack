import pytest
from unittest.mock import MagicMock

from attack.static_attack import StaticAttack


@pytest.fixture
def static_attack():
    return StaticAttack("static", "ornl")


@pytest.fixture
def receiver():
    r = MagicMock()
    r.get_velocity.return_value = (1.0, 2.0, -0.5)
    return r


class TestStaticAttack:

    def test_load_nonexistent_spawn_location_raises_key_error(self):
        with pytest.raises(KeyError):
            StaticAttack("static", "paris")

    def test_compute_spoofed_position_returns_fabric_coords_regardless_of_receiver(self, static_attack, receiver):
        lat, lon, alt = static_attack.compute_spoofed_position(receiver, elapsed_seconds=10.0)
        assert lat == static_attack.fabric_lat
        assert lon == static_attack.fabric_lon
        assert alt == static_attack.fabric_alt

    def test_compute_spoofed_velocity_returns_receiver_velocity_unchanged(self, static_attack, receiver):
        result = static_attack.compute_spoofed_velocity(receiver, elapsed_seconds=10.0)
        assert result == receiver.get_velocity()

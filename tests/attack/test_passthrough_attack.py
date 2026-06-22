import pytest
from unittest.mock import MagicMock

from attack.passthrough_attack import PassthroughAttack


@pytest.fixture
def passthrough_attack():
    return PassthroughAttack("passthrough", "ornl")


@pytest.fixture
def receiver():
    r = MagicMock()
    r.get_position.return_value = (35.9305, -84.3107, 50.0)
    r.get_velocity.return_value = (1.0, 2.0, -0.5)
    return r


class TestPassthroughAttack:

    def test_compute_spoofed_position_returns_receiver_position_unchanged(self, passthrough_attack, receiver):
        result = passthrough_attack.compute_spoofed_position(receiver, elapsed_seconds=10.0)
        assert result == receiver.get_position()

    def test_compute_spoofed_velocity_returns_receiver_velocity_unchanged(self, passthrough_attack, receiver):
        result = passthrough_attack.compute_spoofed_velocity(receiver, elapsed_seconds=10.0)
        assert result == receiver.get_velocity()

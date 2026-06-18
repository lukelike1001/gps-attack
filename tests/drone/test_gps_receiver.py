import pytest
from drone.gps_receiver import GpsReceiver


@pytest.fixture
def receiver():
    r = GpsReceiver()
    r.update_position(35.9305, -84.3107, 50.0)
    r.update_velocity(1.0, 2.0, -0.5)
    return r


class TestGpsReceiver:

    def test_update_position(self, receiver):
        receiver.update_position(10.0, 20.0, 100.0)
        assert receiver.get_position() == (10.0, 20.0, 100.0)

    def test_update_velocity(self, receiver):
        receiver.update_velocity(3.0, 4.0, -1.0)
        assert receiver.get_velocity() == (3.0, 4.0, -1.0)

    def test_get_position_returns_set_values(self, receiver):
        assert receiver.get_position() == (35.9305, -84.3107, 50.0)

    def test_get_velocity_returns_set_values(self, receiver):
        assert receiver.get_velocity() == (1.0, 2.0, -0.5)

    def test_normalize_position(self, receiver):
        norm_lat, norm_lon, norm_alt = receiver.normalize_position(359305000, -843107000, 50000)
        assert norm_lat == pytest.approx(35.9305)
        assert norm_lon == pytest.approx(-84.3107)
        assert norm_alt == pytest.approx(50.0)

    def test_normalize_velocity(self, receiver):
        norm_vx, norm_vy, norm_vz = receiver.normalize_velocity(100, 200, -50)
        assert norm_vx == pytest.approx(1.0)
        assert norm_vy == pytest.approx(2.0)
        assert norm_vz == pytest.approx(-0.5)

    def test_get_signal_quality_params(self, receiver):
        params = receiver.get_signal_quality_params()
        assert isinstance(params["fix_type_3d"], int)
        assert isinstance(params["satellites_visible_count"], int)
        assert isinstance(params["hdop"], float)
        assert isinstance(params["vdop"], float)
        assert isinstance(params["speed_accuracy"], float)
        assert isinstance(params["horizontal_accuracy"], float)
        assert isinstance(params["vertical_accuracy"], float)

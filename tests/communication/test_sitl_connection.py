import pytest
from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock, patch

from communication.sitl_connection import SitlConnection
from communication.sitl_connection_config import ConnectionConfig


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sitl_connection_params.yaml"


@pytest.fixture
def config():
    return ConnectionConfig.from_yaml(FIXTURE_PATH)


@pytest.fixture
def mock_mav():
    mav = MagicMock()
    mav.wait_heartbeat.return_value = True
    return mav


@pytest.fixture
def connected_connection(config, mock_mav):
    with patch("communication.sitl_connection.mavutil") as mock_mavutil:
        mock_mavutil.mavlink_connection.return_value = mock_mav
        conn = SitlConnection(config)
        conn.connect()
    return conn, mock_mav


class TestConnectionConfig:

    def test_from_yaml_maps_connection_address(self):
        config = ConnectionConfig.from_yaml(FIXTURE_PATH)
        assert config.address == "udp:127.0.0.1:14551"

    def test_from_yaml_maps_timeout_and_retry_params(self):
        config = ConnectionConfig.from_yaml(FIXTURE_PATH)
        assert config.heartbeat_timeout_seconds == 5
        assert config.reboot_settle_seconds == 1
        assert config.ack_timeout_seconds == 2
        assert config.max_retries == 2

    def test_from_yaml_maps_ardupilot_param_groups_with_correct_values(self):
        config = ConnectionConfig.from_yaml(FIXTURE_PATH)
        assert config.fence_params["FENCE_ENABLE"] == 1
        assert config.gps_baseline_params["GPS1_TYPE"] == 1
        assert config.gps_attack_params["GPS1_TYPE"] == 14
        assert config.gps_attack_params["GPS_AUTO_SWITCH"] == 0

    def test_from_yaml_raises_on_missing_file(self):
        with pytest.raises(FileNotFoundError):
            ConnectionConfig.from_yaml(Path("nonexistent.yaml"))


class TestSitlConnection:

    def test_connect_uses_configured_address(self, config, mock_mav):
        with patch("communication.sitl_connection.mavutil") as mock_mavutil:
            mock_mavutil.mavlink_connection.return_value = mock_mav
            conn = SitlConnection(config)
            conn.connect()
        mock_mavutil.mavlink_connection.assert_called_once_with(config.address)

    def test_connect_raises_connection_error_on_no_heartbeat(self, config, mock_mav):
        mock_mav.wait_heartbeat.return_value = False
        with patch("communication.sitl_connection.mavutil") as mock_mavutil:
            mock_mavutil.mavlink_connection.return_value = mock_mav
            conn = SitlConnection(config)
            with pytest.raises(ConnectionError):
                conn.connect()

    def test_mav_raises_runtime_error_before_connect(self, config):
        conn = SitlConnection(config)
        with pytest.raises(RuntimeError):
            _ = conn.mav

    def test_close_terminates_mavlink_socket(self, connected_connection):
        conn, mock_mav = connected_connection
        conn.close()
        mock_mav.close.assert_called_once()

    def test_close_discards_mav_handle(self, connected_connection):
        conn, _ = connected_connection
        conn.close()
        with pytest.raises(RuntimeError):
            _ = conn.mav

    def test_close_is_safe_before_connect(self, config):
        conn = SitlConnection(config)
        conn.close()

    def test_set_ardupilot_parameter_returns_true_on_ack(self, connected_connection):
        conn, mock_mav = connected_connection
        ack = MagicMock()
        ack.param_id.rstrip.return_value = "GPS1_TYPE"
        mock_mav.recv_match.return_value = ack
        assert conn.set_ardupilot_parameter("GPS1_TYPE", 14) is True

    def test_set_ardupilot_parameter_returns_false_after_max_retries(self, connected_connection):
        conn, mock_mav = connected_connection
        mock_mav.recv_match.return_value = None
        assert conn.set_ardupilot_parameter("GPS1_TYPE", 14) is False
        assert mock_mav.recv_match.call_count == conn.config.max_retries

    def test_set_all_ardupilot_parameters_baseline_sends_gps_type_1(self, connected_connection):
        conn, mock_mav = connected_connection
        ack = MagicMock()
        ack.param_id.rstrip.return_value = "GPS1_TYPE"
        mock_mav.recv_match.return_value = ack

        conn.set_all_ardupilot_parameters("baseline")

        sent_values = {
            call.args[2].decode(): call.args[3]
            for call in mock_mav.mav.param_set_send.call_args_list
        }
        assert sent_values["GPS1_TYPE"] == 1.0

    def test_set_all_ardupilot_parameters_attack_sends_gps_type_14(self, connected_connection):
        conn, mock_mav = connected_connection
        ack = MagicMock()
        ack.param_id.rstrip.return_value = "GPS1_TYPE"
        mock_mav.recv_match.return_value = ack

        conn.set_all_ardupilot_parameters("attack")

        sent_values = {
            call.args[2].decode(): call.args[3]
            for call in mock_mav.mav.param_set_send.call_args_list
        }
        assert sent_values["GPS1_TYPE"] == 14.0

    def test_reboot_sends_preflight_shutdown_command(self, connected_connection):
        from pymavlink import mavutil as real_mavutil
        conn, mock_mav = connected_connection
        with patch("communication.sitl_connection.time.sleep"), \
             patch.object(conn, "connect"):
            conn.reboot()
        sent_command = mock_mav.mav.command_long_send.call_args.args[2]
        assert sent_command == real_mavutil.mavlink.MAV_CMD_PREFLIGHT_REBOOT_SHUTDOWN

    def test_reboot_closes_connection(self, connected_connection):
        conn, mock_mav = connected_connection
        with patch("communication.sitl_connection.time.sleep"), \
             patch.object(conn, "connect"):
            conn.reboot()
        mock_mav.close.assert_called_once()

    def test_reboot_raises_connection_error_when_sitl_does_not_recover(self, config, mock_mav):
        fast_config = replace(config, reboot_settle_seconds=0)
        with patch("communication.sitl_connection.mavutil") as mock_mavutil:
            mock_mavutil.mavlink_connection.return_value = mock_mav
            conn = SitlConnection(fast_config)
            conn.connect()
        with patch("communication.sitl_connection.time.sleep"), \
             patch.object(conn, "connect", side_effect=ConnectionError):
            with pytest.raises(ConnectionError):
                conn.reboot()

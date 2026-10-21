"""OHH-124: MuJoCo / DDS smoke contract tests (mock-backed; safe without full sim)."""

from __future__ import annotations

import unittest

from ohho_go2.smoke import SimDdsConfig
from ohho_go2.smoke.contract import (
    DEFAULT_MAX_LINEAR_M_S,
    WALK_TEST_DURATION_S,
    WALK_TEST_VELOCITY_M_S,
    MockRobotClient,
    SmokeScenarios,
    clamp_linear_speed,
    refuse_hardware_connect,
    validate_sim_dds,
)


class TestSimDdsGuards(unittest.TestCase):
    def test_sim_dds_domain_and_interface(self) -> None:
        validate_sim_dds(SimDdsConfig())
        with self.assertRaises(ValueError):
            validate_sim_dds(SimDdsConfig(domain_id=0))
        with self.assertRaises(ValueError):
            validate_sim_dds(SimDdsConfig(interface="eth0"))

    def test_hardware_uri_refused_without_arming(self) -> None:
        with self.assertRaises(PermissionError):
            refuse_hardware_connect("unitree://go2/domain=0/eth0", armed=False, is_tty=False)
        with self.assertRaises(PermissionError):
            refuse_hardware_connect("unitree://go2/domain=0/eth0", armed=True, is_tty=False)
        refuse_hardware_connect("sim://go2/domain=1/lo", armed=False, is_tty=False)


class TestVelocityClamp(unittest.TestCase):
    def test_two_m_s_clamped_to_half(self) -> None:
        self.assertEqual(clamp_linear_speed(2.0), DEFAULT_MAX_LINEAR_M_S)
        self.assertEqual(clamp_linear_speed(0.3), 0.3)


class TestSmokeScenarios(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MockRobotClient()
        self.scenarios = SmokeScenarios(self.client)

    def test_connect_and_stand(self) -> None:
        self.scenarios.connect_sim()
        self.assertTrue(self.client.connected)
        self.scenarios.stand()
        self.assertTrue(self.client.standing)

    def test_hardware_connect_refused_on_client(self) -> None:
        with self.assertRaises(PermissionError):
            self.client.connect("unitree://go2/domain=0/wlan0")

    def test_walk_point_three_m_s_for_five_seconds_delta_x(self) -> None:
        self.scenarios.connect_sim()
        self.scenarios.stand()
        delta_x = self.scenarios.walk_forward(WALK_TEST_VELOCITY_M_S, WALK_TEST_DURATION_S)
        expected_min = WALK_TEST_VELOCITY_M_S * WALK_TEST_DURATION_S * 0.9
        expected_max = WALK_TEST_VELOCITY_M_S * WALK_TEST_DURATION_S * 1.1
        self.assertGreaterEqual(delta_x, expected_min)
        self.assertLessEqual(delta_x, expected_max)

    def test_client_kill_watchdog_stops_motion(self) -> None:
        self.scenarios.connect_sim()
        vx = self.scenarios.watchdog_zeros_velocity_after_idle()
        self.assertEqual(vx, 0.0)

    def test_estop_latch(self) -> None:
        self.scenarios.connect_sim()
        self.scenarios.estop_latches()
        with self.assertRaises(RuntimeError):
            self.scenarios.stand()

    def test_clamp_applied_on_move(self) -> None:
        self.scenarios.connect_sim()
        applied = self.scenarios.request_speed_clamped(2.0)
        self.assertEqual(applied, DEFAULT_MAX_LINEAR_M_S)
        self.assertEqual(self.client.last_vx_m_s, DEFAULT_MAX_LINEAR_M_S)


if __name__ == "__main__":
    unittest.main()

"""Unit tests for the sim-only kinematic sensor model (no ROS required)."""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

_NAV_SRC = Path(__file__).resolve().parents[1] / "ros2_ws" / "src" / "ohho_go2_navigation"
if str(_NAV_SRC) not in sys.path:
    sys.path.insert(0, str(_NAV_SRC))

from ohho_go2_navigation.sim_kinematics import (  # noqa: E402
    GO2_JOINT_NAMES,
    GO2_STAND_POSITIONS,
    ROOM_HALF_M,
    SCAN_RANGE_MAX_M,
    SCAN_READINGS,
    SimKinematics,
    room_scan_ranges,
    sensor_timer_period_sec,
)


class TestSimKinematics(unittest.TestCase):
    def test_integrates_forward_velocity(self) -> None:
        kin = SimKinematics()
        kin.set_body_velocity(0.5, 0.0, 0.0, now_s=0.0)
        kin.integrate(0.0)
        kin.integrate(0.2)
        self.assertAlmostEqual(kin.x, 0.1)
        self.assertAlmostEqual(kin.y, 0.0)

    def test_integrates_yaw(self) -> None:
        kin = SimKinematics()
        kin.set_body_velocity(0.0, 0.0, math.pi / 2.0, now_s=0.0)
        kin.integrate(0.0)
        kin.integrate(0.2)
        self.assertAlmostEqual(kin.yaw, math.pi / 10.0)
        qz, qw = kin.yaw_quaternion()
        self.assertAlmostEqual(qz, math.sin(kin.yaw / 2.0))
        self.assertAlmostEqual(qw, math.cos(kin.yaw / 2.0))

    def test_cmd_timeout_zeros_velocity(self) -> None:
        kin = SimKinematics()
        kin.set_body_velocity(0.4, -0.1, 0.2, now_s=0.0)
        self.assertFalse(kin.apply_cmd_timeout(0.2, timeout_s=0.3))
        self.assertEqual(kin.vx, 0.4)
        self.assertTrue(kin.apply_cmd_timeout(0.31, timeout_s=0.3))
        self.assertEqual((kin.vx, kin.vy, kin.vyaw), (0.0, 0.0, 0.0))
        self.assertFalse(kin.apply_cmd_timeout(1.0, timeout_s=0.3))

    def test_scan_at_origin_hits_room_wall(self) -> None:
        ranges = SimKinematics().scan_ranges()
        self.assertEqual(len(ranges), SCAN_READINGS)
        # Beam along +x (index 90 of 180) reaches the wall at x = +3 m.
        self.assertAlmostEqual(ranges[90], 3.0)

    def test_scan_near_wall_reports_far_wall_beyond_five_metres(self) -> None:
        # At x=-2.5 the +x beam hits the wall at +3 m (5.5 m), not a 5 m cap.
        ranges = room_scan_ranges(-2.5, 0.0, 0.0)
        self.assertAlmostEqual(ranges[90], 5.5)

    def test_integrate_stays_inside_room(self) -> None:
        kin = SimKinematics()
        kin.set_body_velocity(1.0, 0.4, 0.0, now_s=0.0)
        kin.integrate(0.0)
        kin.integrate(20.0, dt_cap_s=20.0)
        self.assertAlmostEqual(kin.x, ROOM_HALF_M)
        self.assertAlmostEqual(kin.y, ROOM_HALF_M)
        self.assertLess(kin.scan_ranges()[90], SCAN_RANGE_MAX_M)

        kin = SimKinematics()
        kin.set_body_velocity(-1.0, -0.4, 0.0, now_s=0.0)
        kin.integrate(0.0)
        kin.integrate(20.0, dt_cap_s=20.0)
        self.assertAlmostEqual(kin.x, -ROOM_HALF_M)
        self.assertAlmostEqual(kin.y, -ROOM_HALF_M)

    def test_estop_clears_velocity_and_rejects_later_commands(self) -> None:
        kin = SimKinematics()
        kin.set_body_velocity(0.4, -0.1, 0.2, now_s=0.0)
        kin.latch_estop()
        self.assertTrue(kin.estop_latched)
        self.assertEqual((kin.vx, kin.vy, kin.vyaw), (0.0, 0.0, 0.0))
        kin.set_body_velocity(0.5, 0.1, 0.3, now_s=1.0)
        self.assertEqual((kin.vx, kin.vy, kin.vyaw), (0.0, 0.0, 0.0))
        self.assertEqual(kin.last_cmd_s, 0.0)

    def test_sensor_timer_period_rejects_invalid_rates(self) -> None:
        self.assertAlmostEqual(sensor_timer_period_sec(20.0), 0.05)
        for bad in (0.0, -1.0, float("nan"), float("inf"), float("-inf"), 1e20):
            with self.assertRaises(ValueError):
                sensor_timer_period_sec(bad)

    def test_stand_pose_matches_joint_names(self) -> None:
        self.assertEqual(len(GO2_JOINT_NAMES), 12)
        self.assertEqual(len(GO2_STAND_POSITIONS), len(GO2_JOINT_NAMES))
        self.assertEqual(GO2_JOINT_NAMES[0], "FL_hip_joint")
        self.assertEqual(GO2_STAND_POSITIONS[1], 0.8)
        self.assertEqual(GO2_STAND_POSITIONS[2], -1.5)


class TestSimSensorPackage(unittest.TestCase):
    def test_entry_point_is_registered(self) -> None:
        setup_py = _NAV_SRC / "setup.py"
        text = setup_py.read_text(encoding="utf-8")
        self.assertIn(
            "go2_sim_sensor_node = ohho_go2_navigation.sim_sensor_node:main",
            text,
        )

    def test_sensor_node_source_is_valid_and_has_no_placeholder(self) -> None:
        source = (_NAV_SRC / "ohho_go2_navigation" / "sim_sensor_node.py").read_text(
            encoding="utf-8"
        )
        compile(source, "sim_sensor_node.py", "exec")
        self.assertIn("Sim-only", source)
        self.assertNotIn("NotImplementedError", source)
        self.assertIn('"/ohho/estop"', source)
        self.assertIn("latch_estop", source)
        self.assertIn("from rclpy.clock import Clock, ClockType", source)
        self.assertIn("from rclpy.clock_type import ClockType", source)


if __name__ == "__main__":
    unittest.main()

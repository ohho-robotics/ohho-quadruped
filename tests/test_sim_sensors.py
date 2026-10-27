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
    SCAN_READINGS,
    SimKinematics,
    room_scan_ranges,
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


if __name__ == "__main__":
    unittest.main()

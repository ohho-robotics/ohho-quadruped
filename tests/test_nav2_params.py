"""Unit tests for Nav2 and SLAM parameters (stdlib unittest, no ROS required)."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_NAV_DIR = _REPO_ROOT / "ros2_ws" / "src" / "ohho_go2_navigation"


def _extract_yaml_value(text: str, key: str) -> str | None:
    """Simple regex helper to extract a value from yaml text."""
    pattern = rf"^\s*{re.escape(key)}:\s*(.+)$"
    m = re.search(pattern, text, re.MULTILINE)
    return m.group(1).strip() if m else None


class TestNav2Params(unittest.TestCase):
    def setUp(self) -> None:
        self.nav2_yaml = _NAV_DIR / "config" / "nav2_params.yaml"
        self.slam_yaml = _NAV_DIR / "config" / "slam_toolbox_params.yaml"
        self.assertTrue(self.nav2_yaml.exists(), "nav2_params.yaml missing")
        self.assertTrue(self.slam_yaml.exists(), "slam_toolbox_params.yaml missing")
        self.nav2_text = self.nav2_yaml.read_text(encoding="utf-8")
        self.slam_text = self.slam_yaml.read_text(encoding="utf-8")

    def test_footprint_dimensions(self) -> None:
        """Footprint must match Go2 dimensions: ~0.70m length x 0.31m width."""
        m = re.search(r'footprint:\s*"(\[\[.+?\]\])"', self.nav2_text)
        self.assertIsNotNone(m, "footprint parameter not found in nav2_params.yaml")
        raw_footprint = m.group(1)
        coords = json.loads(raw_footprint)
        self.assertEqual(len(coords), 4, "Go2 footprint should be a 4-point polygon")

        xs = [pt[0] for pt in coords]
        ys = [pt[1] for pt in coords]
        length = max(xs) - min(xs)
        width = max(ys) - min(ys)

        self.assertAlmostEqual(length, 0.70, delta=0.05, msg="Go2 length should be ~0.70m")
        self.assertAlmostEqual(width, 0.31, delta=0.03, msg="Go2 width should be ~0.31m")

    def test_velocity_caps_match_safety_gate(self) -> None:
        """Nav2 velocity caps must match SafetyGate limits: 0.5 lin, 0.3 lat, 1.0 yaw."""
        max_vx = float(_extract_yaml_value(self.nav2_text, "max_vel_x"))
        max_vy = float(_extract_yaml_value(self.nav2_text, "max_vel_y"))
        max_vtheta = float(_extract_yaml_value(self.nav2_text, "max_vel_theta"))
        max_speed = float(_extract_yaml_value(self.nav2_text, "max_speed_xy"))

        self.assertLessEqual(max_vx, 0.5)
        self.assertLessEqual(max_vy, 0.3)
        self.assertLessEqual(max_vtheta, 1.0)
        self.assertLessEqual(max_speed, 0.5)

        # Behavior server rotational velocity cap
        max_rot = float(_extract_yaml_value(self.nav2_text, "max_rotational_vel"))
        self.assertLessEqual(max_rot, 1.0)

    def test_slam_toolbox_params(self) -> None:
        """SLAM Toolbox must be configured for online async mapping from /scan."""
        scan_topic = _extract_yaml_value(self.slam_text, "scan_topic")
        mode = _extract_yaml_value(self.slam_text, "mode")
        odom_frame = _extract_yaml_value(self.slam_text, "odom_frame")
        base_frame = _extract_yaml_value(self.slam_text, "base_frame")
        map_frame = _extract_yaml_value(self.slam_text, "map_frame")

        self.assertEqual(scan_topic, "/scan")
        self.assertEqual(mode, "mapping")
        self.assertEqual(odom_frame, "odom")
        self.assertEqual(base_frame, "base_link")
        self.assertEqual(map_frame, "map")

    def test_navigation_rviz_config_exists(self) -> None:
        rviz_file = _NAV_DIR / "config" / "rviz_nav2.rviz"
        self.assertTrue(rviz_file.exists(), "rviz_nav2.rviz missing")
        text = rviz_file.read_text(encoding="utf-8")
        self.assertIn("/scan", text)
        self.assertIn("/map", text)
        self.assertIn("/global_costmap/costmap", text)
        self.assertIn("/local_costmap/costmap", text)


if __name__ == "__main__":
    unittest.main()

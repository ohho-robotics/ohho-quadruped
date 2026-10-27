"""Unit tests for go2_nav_sim launch scripts (stdlib unittest, no ROS required)."""

from __future__ import annotations

import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_NAV_DIR = _REPO_ROOT / "ros2_ws" / "src" / "ohho_go2_navigation"


class TestNavSimLaunch(unittest.TestCase):
    def test_package_xml(self) -> None:
        pkg_xml = _NAV_DIR / "package.xml"
        self.assertTrue(pkg_xml.exists(), "package.xml missing in ohho_go2_navigation")
        tree = ET.parse(pkg_xml)
        root = tree.getroot()
        name_el = root.find("name")
        self.assertIsNotNone(name_el)
        self.assertEqual(name_el.text, "ohho_go2_navigation")

        exec_deps = {el.text for el in root.findall("exec_depend")}
        self.assertIn("nav2_bringup", exec_deps)
        self.assertIn("slam_toolbox", exec_deps)
        self.assertIn("go2_description", exec_deps)
        self.assertIn("ohho_go2_bridge", exec_deps)

    def test_go2_nav_sim_launch_syntax(self) -> None:
        launch_file = _NAV_DIR / "launch" / "go2_nav_sim.launch.py"
        self.assertTrue(launch_file.exists(), "go2_nav_sim.launch.py missing")
        text = launch_file.read_text(encoding="utf-8")
        compile(text, str(launch_file), "exec")

        # Inspect declared launch arguments and components
        self.assertIn("use_sim_time", text)
        self.assertIn("headless", text)
        self.assertIn("use_mock_sim", text)
        self.assertIn("scene", text)
        self.assertIn("default_value=\"office\"", text)
        self.assertIn("robot_state_publisher", text)
        self.assertIn("ohho_go2_bridge", text)
        self.assertIn("go2_sim_sensor_node", text)
        self.assertIn("IfCondition(use_mock_sim)", text)
        self.assertNotIn("publish_sim_sensors", text)
        self.assertIn("slam_toolbox", text)
        self.assertIn("nav2.launch.py", text)
        self.assertIn("ROS_DOMAIN_ID=0 is not allowed for simulation", text)
        self.assertIn("go2_description URDF not found", text)
        self.assertIn("sim/run_go2.py", text)

    def test_nav2_launch_syntax(self) -> None:
        launch_file = _NAV_DIR / "launch" / "nav2.launch.py"
        self.assertTrue(launch_file.exists(), "nav2.launch.py missing")
        text = launch_file.read_text(encoding="utf-8")
        compile(text, str(launch_file), "exec")
        self.assertIn("controller_server", text)
        self.assertIn("planner_server", text)
        self.assertIn("bt_navigator", text)
        self.assertIn("lifecycle_manager_navigation", text)

    def test_slam_launch_syntax(self) -> None:
        launch_file = _NAV_DIR / "launch" / "slam.launch.py"
        self.assertTrue(launch_file.exists(), "slam.launch.py missing")
        text = launch_file.read_text(encoding="utf-8")
        compile(text, str(launch_file), "exec")
        self.assertIn("async_slam_toolbox_node", text)


if __name__ == "__main__":
    unittest.main()

"""Unit tests for go2_description package (stdlib unittest, no ROS required)."""

from __future__ import annotations

import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DESC_DIR = _REPO_ROOT / "ros2_ws" / "src" / "go2_description"

EXPECTED_JOINTS = {
    "FL_hip_joint",
    "FL_thigh_joint",
    "FL_calf_joint",
    "FR_hip_joint",
    "FR_thigh_joint",
    "FR_calf_joint",
    "RL_hip_joint",
    "RL_thigh_joint",
    "RL_calf_joint",
    "RR_hip_joint",
    "RR_thigh_joint",
    "RR_calf_joint",
}

EXPECTED_LINKS = {
    "base_link",
    "base",
    "radar",
    "imu",
    "front_camera",
    "FL_hip",
    "FL_thigh",
    "FL_calf",
    "FL_foot",
    "FR_hip",
    "FR_thigh",
    "FR_calf",
    "FR_foot",
    "RL_hip",
    "RL_thigh",
    "RL_calf",
    "RL_foot",
    "RR_hip",
    "RR_thigh",
    "RR_calf",
    "RR_foot",
}


class TestGo2Description(unittest.TestCase):
    def test_package_xml(self) -> None:
        pkg_xml = _DESC_DIR / "package.xml"
        self.assertTrue(pkg_xml.exists(), "package.xml missing")
        tree = ET.parse(pkg_xml)
        root = tree.getroot()
        name_el = root.find("name")
        self.assertIsNotNone(name_el)
        self.assertEqual(name_el.text, "go2_description")
        lic_el = root.find("license")
        self.assertIsNotNone(lic_el)
        self.assertEqual(lic_el.text, "BSD-3-Clause")

    def test_license_file(self) -> None:
        lic_file = _DESC_DIR / "LICENSE"
        self.assertTrue(lic_file.exists(), "LICENSE missing in go2_description")
        text = lic_file.read_text(encoding="utf-8")
        self.assertIn("BSD 3-Clause License", text)
        self.assertIn("Unitree Robotics", text)

    def test_urdf_structure_and_links(self) -> None:
        urdf_path = _DESC_DIR / "urdf" / "go2_description.urdf"
        self.assertTrue(urdf_path.exists(), "go2_description.urdf missing")
        tree = ET.parse(urdf_path)
        root = tree.getroot()
        self.assertEqual(root.tag, "robot")

        links = {el.attrib["name"] for el in root.findall("link")}
        joints = {el.attrib["name"] for el in root.findall("joint")}

        for expected in EXPECTED_LINKS:
            self.assertIn(expected, links, f"Expected link {expected} not in URDF")

        for expected in EXPECTED_JOINTS:
            self.assertIn(expected, joints, f"Expected joint {expected} not in URDF")

        self.assertIn("base_link_to_base", joints)
        self.assertIn("radar_joint", joints)

    def test_meshes_exist(self) -> None:
        urdf_path = _DESC_DIR / "urdf" / "go2_description.urdf"
        text = urdf_path.read_text(encoding="utf-8")
        import re

        mesh_refs = re.findall(r'package://go2_description/meshes/([^"]+)', text)
        self.assertGreater(len(mesh_refs), 0, "No mesh references found in URDF")
        for mesh_name in set(mesh_refs):
            mesh_file = _DESC_DIR / "meshes" / mesh_name
            self.assertTrue(
                mesh_file.exists(),
                f"Referenced mesh missing: {mesh_file}",
            )
            self.assertGreater(mesh_file.stat().st_size, 0)

    def test_display_launch_syntax(self) -> None:
        launch_file = _DESC_DIR / "launch" / "display.launch.py"
        self.assertTrue(launch_file.exists(), "display.launch.py missing")
        text = launch_file.read_text(encoding="utf-8")
        compile(text, str(launch_file), "exec")
        self.assertIn("generate_launch_description", text)
        self.assertIn("robot_state_publisher", text)
        self.assertIn("use_bridge_joint_states", text)
        self.assertIn("joint_state_publisher_gui", text)
        self.assertIn("read_text", text)
        self.assertNotIn("Command(", text)
        pkg_xml = (_DESC_DIR / "package.xml").read_text(encoding="utf-8")
        self.assertIn("joint_state_publisher_gui", pkg_xml)

    def test_rviz_config_exists(self) -> None:
        rviz_file = _DESC_DIR / "rviz" / "go2.rviz"
        self.assertTrue(rviz_file.exists(), "rviz/go2.rviz missing")
        text = rviz_file.read_text(encoding="utf-8")
        self.assertIn("RobotModel", text)
        self.assertIn("base_link", text)


if __name__ == "__main__":
    unittest.main()

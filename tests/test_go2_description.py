"""Unit tests for go2_description package (stdlib unittest, no ROS required)."""

from __future__ import annotations

import importlib.util
import math
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
        self.assertIn("use_joint_state_publisher_gui", text)
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

    def test_gazebo_launch_is_visual_only(self) -> None:
        launch_file = _DESC_DIR / "launch" / "gazebo.launch.py"
        self.assertTrue(launch_file.exists(), "gazebo.launch.py missing")
        text = launch_file.read_text(encoding="utf-8")
        compile(text, str(launch_file), "exec")
        self.assertIn("ros_gz_sim", text)
        self.assertIn("executable=\"create\"", text)
        self.assertIn("robot_state_publisher", text)
        self.assertIn("standing", text)
        self.assertIn("lying", text)
        self.assertNotIn("controller_manager", text)
        self.assertNotIn("gazebo_ros_control", text)
        self.assertNotIn("robot_control.yaml", text)

    def test_spawn_pose_stands_and_lies(self) -> None:
        spawn_pose = _load_spawn_pose()
        urdf_path = _DESC_DIR / "urdf" / "go2_description.urdf"
        original = urdf_path.read_text(encoding="utf-8")
        standing = spawn_pose.build_spawn(original, "standing")
        lying = spawn_pose.build_spawn(original, "lying")
        self.assertEqual(urdf_path.read_text(encoding="utf-8"), original)

        _assert_joint_rotation(
            spawn_pose,
            _joint_rpy(standing.urdf, "FL_calf_joint"),
            (0.0, 1.0, 0.0),
            spawn_pose.POSE_ANGLES["standing"]["calf"],
        )
        _assert_joint_rotation(
            spawn_pose,
            _joint_rpy(lying.urdf, "FL_calf_joint"),
            (0.0, 1.0, 0.0),
            spawn_pose.POSE_ANGLES["lying"]["calf"],
        )
        _assert_joint_rotation(
            spawn_pose,
            _joint_rpy(standing.urdf, "FL_thigh_joint"),
            (0.0, 1.0, 0.0),
            spawn_pose.POSE_ANGLES["standing"]["thigh"],
        )
        self.assertAlmostEqual(standing.roll, 0.0, places=5)
        self.assertAlmostEqual(lying.roll, math.pi / 2.0, places=5)
        self.assertGreater(standing.z, 0.15)
        self.assertGreater(lying.z, 0.0)

        for spec in (standing, lying):
            root = ET.fromstring(spec.urdf)
            static = root.find("gazebo/static")
            self.assertIsNotNone(static)
            self.assertEqual(static.text, "true")
            self.assertNotIn("plugin", spec.urdf)
            low = spawn_pose.lowest_sample_z(spec.urdf, spec.roll, spec.pitch, spec.yaw, spec.z)
            self.assertAlmostEqual(low, spawn_pose.GROUND_CLEARANCE, places=3)
            for prefix in ("FL", "FR", "RL", "RR"):
                for part in ("hip", "thigh", "calf"):
                    joint = _joint(root, f"{prefix}_{part}_joint")
                    self.assertEqual(joint.get("type"), "fixed")
                    self.assertIsNone(joint.find("axis"))

        resolved = spawn_pose.build_spawn(original, "standing", package_root=_DESC_DIR)
        mesh = f"{_DESC_DIR.as_posix()}/meshes/foot.dae"
        self.assertIn(mesh, resolved.urdf)
        self.assertNotIn("package://go2_description/", resolved.urdf)

    def test_sim_only_no_gait_controller_copy(self) -> None:
        phrase = "sim only, no gait controller"
        pkg = (_DESC_DIR / "README.md").read_text(encoding="utf-8").lower()
        root = (_REPO_ROOT / "README.md").read_text(encoding="utf-8").lower()
        self.assertIn(phrase, pkg)
        self.assertIn(phrase, root)

    def test_ci_checks_urdf_and_launch_args(self) -> None:
        workflow = (_REPO_ROOT / ".github" / "workflows" / "ros2-nav2.yml").read_text(
            encoding="utf-8"
        )
        script = (_REPO_ROOT / "scripts" / "ci" / "check-go2-description.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("scripts/ci/check-go2-description.sh", workflow)
        self.assertIn("check_urdf", script)
        self.assertIn("display.launch.py --show-args", script)
        self.assertIn("gazebo.launch.py --show-args", script)
        self.assertIn("standing", script)
        self.assertIn("lying", script)
        self.assertIn("xacro/robot.xacro", script)


def _load_spawn_pose():
    path = _DESC_DIR / "launch" / "spawn_pose.py"
    spec = importlib.util.spec_from_file_location("go2_spawn_pose", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _joint(root: ET.Element, name: str) -> ET.Element:
    for joint in root.findall("joint"):
        if joint.get("name") == name:
            return joint
    raise AssertionError(f"missing joint {name}")


def _joint_rpy(urdf: str, name: str) -> tuple[float, float, float]:
    origin = _joint(ET.fromstring(urdf), name).find("origin")
    assert origin is not None
    roll, pitch, yaw = (float(item) for item in origin.get("rpy", "").split())
    return roll, pitch, yaw


def _assert_joint_rotation(spawn_pose, rpy, axis, angle) -> None:
    got = spawn_pose._rpy_matrix(*rpy)
    expected = spawn_pose._axis_matrix(axis, angle)
    err = max(abs(got[i][j] - expected[i][j]) for i in range(3) for j in range(3))
    if err >= 1e-6:
        raise AssertionError(f"rotation error {err} for angle {angle}")


if __name__ == "__main__":
    unittest.main()

"""Tests for OhhO Go2 MuJoCo sim launcher and scenes."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from sim.dds_guard import validate_dds_endpoint  # noqa: E402
from sim.mjcf import compose_scene_xml, load_model_and_data, scene_env_fragment  # noqa: E402
from sim.pins import FRONT_CAMERA_NAME, SCENE_CHOICES, UNITREE_MUJOCO_REF  # noqa: E402
from sim.run_go2 import build_parser  # noqa: E402
from sim.scene_objects import SCENE_OBJECTS  # noqa: E402
from sim.unitree_paths import read_checkout_ref, resolve_unitree_mujoco_root  # noqa: E402


def _unitree_mujoco_root_for_tests() -> Path | None:
    env = os.environ.get("OHHO_UNITREE_MUJOCO_ROOT")
    if env:
        p = Path(env)
        return p if p.is_dir() else None
    local = _REPO / ".tmp-unitree_mujoco"
    return local if local.is_dir() else None


class TestRunGo2Cli(unittest.TestCase):
    def test_defaults(self) -> None:
        args = build_parser().parse_args([])
        self.assertEqual(args.scene, "flat")
        self.assertEqual(args.domain, 1)
        self.assertEqual(args.iface, "lo")
        self.assertFalse(args.headless)
        self.assertTrue(args.no_joystick is False)

    def test_headless_office(self) -> None:
        args = build_parser().parse_args(["--headless", "--scene", "office", "--no-joystick"])
        self.assertTrue(args.headless)
        self.assertEqual(args.scene, "office")
        self.assertTrue(args.no_joystick)


class TestDdsGuard(unittest.TestCase):
    def test_sim_defaults_allowed(self) -> None:
        validate_dds_endpoint(1, "lo")

    def test_non_sim_refused_without_arm(self) -> None:
        with self.assertRaises(SystemExit):
            validate_dds_endpoint(0, "eth0")


class TestSceneFragments(unittest.TestCase):
    def test_env_files_exist(self) -> None:
        for scene in SCENE_CHOICES:
            path = scene_env_fragment(scene)
            text = path.read_text(encoding="utf-8")
            for obj in SCENE_OBJECTS[scene]:
                self.assertIn(f'name="{obj["name"]}"', text)

    def test_compose_includes_go2(self) -> None:
        xml = compose_scene_xml("flat")
        self.assertIn('<include file="go2.xml"/>', xml)


class TestMjcfIntegration(unittest.TestCase):
    def setUp(self) -> None:
        self.root = _unitree_mujoco_root_for_tests()
        if self.root is None:
            self.skipTest(
                "set OHHO_UNITREE_MUJOCO_ROOT or clone .tmp-unitree_mujoco for MJCF tests"
            )

    def test_pin_matches_when_git_checkout(self) -> None:
        head = read_checkout_ref(self.root)
        if head is not None:
            self.assertEqual(head, UNITREE_MUJOCO_REF)

    def test_load_flat_has_camera_and_objects(self) -> None:
        os.environ["OHHO_UNITREE_MUJOCO_ROOT"] = str(self.root)
        model, _data = load_model_and_data("flat", resolve_unitree_mujoco_root())
        import mujoco

        cam = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_CAMERA, FRONT_CAMERA_NAME)
        self.assertGreaterEqual(cam, 0)
        for obj in SCENE_OBJECTS["flat"]:
            gid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, obj["name"])
            self.assertGreaterEqual(gid, 0, msg=obj["name"])


if __name__ == "__main__":
    unittest.main()

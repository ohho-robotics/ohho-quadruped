"""Stdlib unittest for scripts/rehearse_sport_motion.py.

CI runs ``python -m unittest discover -s tests``. This repo does not use pytest.
"""

from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import rehearse_sport_motion as rsm  # noqa: E402, I001


_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "rehearse_sport_motion.py"
_BANNED_MODULES = frozenset(
    {
        "socket",
        "cyclonedds",
        "unitree_sdk2py",
        "subprocess",
        "asyncio",
    }
)


def _imported_modules(source: str) -> set[str]:
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".", 1)[0])
    return names


class RehearseSportMotionTest(unittest.TestCase):
    def test_source_imports_no_dds_or_socket(self) -> None:
        imported = _imported_modules(_SCRIPT.read_text(encoding="utf-8"))
        self.assertTrue(_BANNED_MODULES.isdisjoint(imported))

    def test_rehearsal_steps_pass(self) -> None:
        rows = rsm.rehearse()
        self.assertTrue(rows)
        self.assertTrue(all(row["result"] == "PASS" for row in rows))
        checks = {row["check"] for row in rows}
        self.assertIn("stand_lie_x5", checks)
        self.assertIn("cap_vx", checks)
        self.assertIn("ohho_estop", checks)
        self.assertIn("client_watchdog", checks)
        self.assertIn("remote_damp", checks)

    def test_velocity_cap_and_estop_zero(self) -> None:
        robot = rsm.FakeTransport(posture="standing")
        robot.command("move", 2.0, 1.0, 3.0)
        self.assertEqual(robot.vx, rsm.MAX_VX_M_S)
        self.assertEqual(robot.vy, rsm.MAX_VY_M_S)
        self.assertEqual(robot.w, rsm.MAX_WZ_RAD_S)

        robot.emergency_stop()
        self.assertEqual((robot.vx, robot.vy, robot.w), (0.0, 0.0, 0.0))
        self.assertTrue(robot.latched)
        self.assertFalse(robot.command("move", 0.3, 0.0, 0.0))
        self.assertEqual(robot.vx, 0.0)

        watched = rsm.FakeTransport(posture="standing")
        watched.command("move", 0.3, 0.0, 0.0)
        watched.advance(rsm.CMD_TIMEOUT_S)
        self.assertEqual(watched.vx, 0.0)
        self.assertFalse(watched.latched)

        remote = rsm.FakeTransport(posture="standing")
        remote.command("move", 0.3, 0.0, 0.0)
        remote.remote_damp()
        self.assertEqual((remote.vx, remote.vy, remote.w), (0.0, 0.0, 0.0))

    def test_main_fake_transport_exits_zero(self) -> None:
        self.assertEqual(rsm.main([]), 0)

    def test_main_refuses_dds_transport(self) -> None:
        code = rsm.main(["--transport", "dds://eth0?domain=0"])
        self.assertEqual(code, 2)
        code_lo = rsm.main(["--transport", "dds://lo?domain=1"])
        self.assertEqual(code_lo, 2)


if __name__ == "__main__":
    unittest.main()

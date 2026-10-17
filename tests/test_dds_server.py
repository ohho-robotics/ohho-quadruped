"""Headless tests for the sport DDS server. No MuJoCo and no Unitree SDK."""

from __future__ import annotations

import unittest

from ohho_go2 import sport_api as api
from ohho_go2.dds_guard import SimDdsRefusalError
from ohho_go2.dds_server import SportDdsServer, apply_motor_commands, main, make_sport_handler
from ohho_go2.sport_shim import MotorCommand, SportShimEngine


class _Slot:
    def __init__(self) -> None:
        self.mode = 0
        self.q = 0.0
        self.dq = 0.0
        self.tau = 0.0
        self.kp = 0.0
        self.kd = 0.0


class TestApplyMotorCommands(unittest.TestCase):
    def test_writes_twelve_slots_and_leaves_the_rest(self) -> None:
        slots = [_Slot() for _ in range(20)]
        motors = [MotorCommand(q=0.67, dq=0.1, kp=60.0, kd=5.0, tau=0.2) for _ in range(12)]
        apply_motor_commands(slots, motors)
        self.assertEqual(slots[0].mode, 1)
        self.assertAlmostEqual(slots[11].q, 0.67)
        self.assertAlmostEqual(slots[11].kd, 5.0)
        self.assertEqual(slots[12].mode, 0)
        self.assertEqual(slots[19].q, 0.0)


class TestSportHandler(unittest.TestCase):
    def test_stand_up_and_move_zero(self) -> None:
        engine = SportShimEngine()
        stand = make_sport_handler(engine, api.ROBOT_SPORT_API_ID_STANDUP)
        code, message = stand("{}")
        self.assertEqual(code, 0)
        self.assertIn("ok", message)
        move = make_sport_handler(engine, api.ROBOT_SPORT_API_ID_MOVE)
        code, _ = move('{"x": 0.2, "y": 0, "z": 0}')
        self.assertEqual(code, 0)
        self.assertAlmostEqual(engine.move_vx, 0.2)
        code, _ = move('{"x": 0, "y": 0, "z": 0}')
        self.assertEqual(code, 0)
        self.assertEqual(engine.move_vx, 0.0)


class TestSportDdsServerGuard(unittest.TestCase):
    def test_refuses_domain_0(self) -> None:
        with self.assertRaises(SimDdsRefusalError):
            SportDdsServer(domain=0, interface="lo")

    def test_refuses_non_loopback(self) -> None:
        with self.assertRaises(SimDdsRefusalError):
            SportDdsServer(domain=1, interface="eth0")

    def test_cli_refuses_domain_0(self) -> None:
        self.assertEqual(main(["--domain", "0", "--interface", "lo"]), 2)

    def test_start_without_sdk_exits_clearly(self) -> None:
        try:
            import unitree_sdk2py  # type: ignore  # noqa: F401
        except ImportError:
            pass
        else:
            self.skipTest("unitree_sdk2py is installed; not starting DDS from tests")
        server = SportDdsServer()
        with self.assertRaises(SystemExit) as ctx:
            server.start()
        self.assertIn("unitree_sdk2py", str(ctx.exception))

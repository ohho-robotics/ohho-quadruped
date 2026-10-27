"""Unit tests for ohho_go2_bridge pure-Python modules (no ROS install required)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_BRIDGE_SRC = Path(__file__).resolve().parents[1] / "ros2_ws" / "src" / "ohho_go2_bridge"
if str(_BRIDGE_SRC) not in sys.path:
    sys.path.insert(0, str(_BRIDGE_SRC))

from ohho_go2_bridge.cmd_vel_bridge import CmdVelBridge  # noqa: E402
from ohho_go2_bridge.domain_guard import (  # noqa: E402
    CONFIRM_PHRASE,
    DomainRefusedError,
    require_safe_ros_domain,
)
from ohho_go2_bridge.mode_allowlist import resolve_mode  # noqa: E402
from ohho_go2_bridge.transport import MockSportTransport  # noqa: E402
from ohho_go2_bridge.velocity_limits import clamp_twist  # noqa: E402
from ohho_go2_bridge.watchdog import CmdVelWatchdog  # noqa: E402


class TestVelocityClamp(unittest.TestCase):
    def test_clamps_to_defaults(self) -> None:
        lx, ly, az, clamped = clamp_twist(9.0, -9.0, 9.0)
        self.assertTrue(clamped)
        self.assertEqual(lx, 0.5)
        self.assertEqual(ly, -0.3)
        self.assertEqual(az, 1.0)

    def test_passes_small_commands(self) -> None:
        lx, ly, az, clamped = clamp_twist(0.1, 0.0, 0.2)
        self.assertFalse(clamped)
        self.assertEqual((lx, ly, az), (0.1, 0.0, 0.2))


class TestDomainGuard(unittest.TestCase):
    def test_nonzero_domain_allowed(self) -> None:
        domain = require_safe_ros_domain(env={"ROS_DOMAIN_ID": "1"})
        self.assertEqual(domain, 1)

    def test_domain_zero_without_arm_fails(self) -> None:
        with self.assertRaises(DomainRefusedError):
            require_safe_ros_domain(
                env={"ROS_DOMAIN_ID": "0"},
                stdin_is_tty=True,
                prompt=lambda _: CONFIRM_PHRASE,
            )

    def test_domain_zero_non_tty_fails(self) -> None:
        env = {"ROS_DOMAIN_ID": "0", "OHHO_ARM_HARDWARE": "1"}
        with self.assertRaises(DomainRefusedError):
            require_safe_ros_domain(env=env, stdin_is_tty=False)

    def test_domain_zero_armed_with_confirm(self) -> None:
        env = {"ROS_DOMAIN_ID": "0", "OHHO_ARM_HARDWARE": "1"}
        logged: list[str] = []

        domain = require_safe_ros_domain(
            env=env,
            stdin_is_tty=True,
            prompt=lambda _: CONFIRM_PHRASE,
            log_confirm=logged.append,
        )
        self.assertEqual(domain, 0)
        self.assertEqual(len(logged), 1)


class TestCmdVelWatchdog(unittest.TestCase):
    def test_stop_after_timeout(self) -> None:
        transport = MockSportTransport()
        bridge = CmdVelBridge(transport, CmdVelWatchdog(timeout_sec=0.3))
        bridge.on_cmd_vel(0.1, 0.0, 0.0, now_monotonic=0.0)
        self.assertFalse(bridge.tick_watchdog(0.2))
        self.assertTrue(bridge.tick_watchdog(0.31))
        self.assertEqual(transport.stop_count, 1)
        self.assertEqual(transport.moves[-1], (0.1, 0.0, 0.0))


class TestModeAllowlist(unittest.TestCase):
    def test_stand_and_lie(self) -> None:
        self.assertEqual(resolve_mode("stand"), "stand_up")
        self.assertEqual(resolve_mode("lie"), "stand_down")

    def test_forbidden(self) -> None:
        with self.assertRaises(ValueError):
            resolve_mode("flip")


if __name__ == "__main__":
    unittest.main()

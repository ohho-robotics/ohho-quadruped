"""Headless tests for ohho_go2.sport_shim (mocks only — no MuJoCo / hardware)."""

from __future__ import annotations

import unittest

from ohho_go2 import sport_api as api
from ohho_go2.dds_guard import SimDdsRefusalError, assert_sim_dds_only
from ohho_go2.sport_shim import (
    MOVE_COMMAND_TIMEOUT_S,
    ShimPhase,
    SportShim,
    SportShimEngine,
)


class FakeClock:
    def __init__(self, t: float = 0.0) -> None:
        self.t = t

    def now(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


def engine_with_clock(t0: float = 0.0) -> tuple[SportShimEngine, FakeClock]:
    clock = FakeClock(t0)
    eng = SportShimEngine(_time_fn=clock.now)
    return eng, clock


class TestDdsGuard(unittest.TestCase):
    def test_accepts_domain_1_lo(self) -> None:
        assert_sim_dds_only(1, "lo")

    def test_refuses_domain_0(self) -> None:
        with self.assertRaises(SimDdsRefusalError):
            assert_sim_dds_only(0, "lo")

    def test_refuses_non_lo_interface(self) -> None:
        with self.assertRaises(SimDdsRefusalError):
            assert_sim_dds_only(1, "eth0")

    def test_sport_shim_constructor_refuses_hardware_dds(self) -> None:
        with self.assertRaises(SimDdsRefusalError):
            SportShim(domain=0, interface="lo")


class TestSportApiHandling(unittest.TestCase):
    def test_unknown_api_returns_error(self) -> None:
        eng, _ = engine_with_clock()
        code, msg = eng.handle_api(1015, "{}")
        self.assertNotEqual(code, 0)
        self.assertIn("unsupported", msg)

    def test_stand_up_then_walk_stub(self) -> None:
        eng, clock = engine_with_clock()
        code, _ = eng.handle_api(api.ROBOT_SPORT_API_ID_STANDUP, None)
        self.assertEqual(code, 0)
        clock.advance(3.0)
        eng.tick()
        self.assertEqual(eng.phase, ShimPhase.STANDING)

        code, _ = eng.handle_api(
            api.ROBOT_SPORT_API_ID_MOVE,
            '{"x": 0.2, "y": 0.0, "z": 0.0}',
        )
        self.assertEqual(code, 0)
        self.assertEqual(eng.phase, ShimPhase.WALKING)
        motors, state = eng.tick()
        self.assertEqual(len(motors), 12)
        self.assertTrue(state.policy_stub)
        self.assertEqual(state.gait_type, 255)

    def test_move_refused_while_lying(self) -> None:
        eng, _ = engine_with_clock()
        code, msg = eng.handle_api(api.ROBOT_SPORT_API_ID_MOVE, '{"x": 0.1}')
        self.assertEqual(code, 3)
        self.assertIn("not standing", msg)

    def test_move_times_out_to_zero(self) -> None:
        eng, clock = engine_with_clock()
        eng.phase = ShimPhase.STANDING
        eng.handle_api(api.ROBOT_SPORT_API_ID_MOVE, '{"x": 0.3, "y": 0, "z": 0.2}')
        self.assertEqual(eng.phase, ShimPhase.WALKING)
        clock.advance(MOVE_COMMAND_TIMEOUT_S + 0.05)
        eng.tick()
        self.assertEqual(eng.move_vx, 0.0)
        self.assertEqual(eng.move_vyaw, 0.0)
        self.assertEqual(eng.phase, ShimPhase.STANDING)

    def test_stop_move_clears_velocity(self) -> None:
        eng, _ = engine_with_clock()
        eng.phase = ShimPhase.WALKING
        eng.move_vx = 0.2
        code, _ = eng.handle_api(api.ROBOT_SPORT_API_ID_STOPMOVE, None)
        self.assertEqual(code, 0)
        self.assertEqual(eng.move_vx, 0.0)
        self.assertEqual(eng.phase, ShimPhase.STANDING)

    def test_damp_estop_latches(self) -> None:
        eng, _ = engine_with_clock()
        eng.phase = ShimPhase.WALKING
        code, _ = eng.handle_api(api.ROBOT_SPORT_API_ID_DAMP, None)
        self.assertEqual(code, 0)
        self.assertTrue(eng.latched_estop)
        self.assertEqual(eng.phase, ShimPhase.DAMPING)
        code2, _ = eng.handle_api(api.ROBOT_SPORT_API_ID_STANDUP, None)
        self.assertNotEqual(code2, 0)
        motors, state = eng.tick()
        self.assertEqual(motors[0].kp, 0.0)
        self.assertEqual(state.error_code, 1)

    def test_euler_clamped(self) -> None:
        eng, _ = engine_with_clock()
        eng.phase = ShimPhase.STANDING
        eng.handle_api(api.ROBOT_SPORT_API_ID_EULER, '{"x": 1.0, "y": -1.0, "z": 0.5}')
        self.assertAlmostEqual(eng.euler_roll, 0.3)
        self.assertAlmostEqual(eng.euler_pitch, -0.3)
        self.assertAlmostEqual(eng.euler_yaw, 0.3)


class TestSportShimDdsWrapper(unittest.TestCase):
    def test_step_invokes_publishers(self) -> None:
        published_motors: list[int] = []
        published_states: list[str] = []

        def on_lowcmd(motors: object) -> None:
            published_motors.append(len(list(motors)))  # type: ignore[arg-type]

        def on_state(state: object) -> None:
            published_states.append(getattr(state, "shim_phase"))

        shim = SportShim(domain=1, interface="lo", engine=SportShimEngine())
        shim.connect(publish_lowcmd=on_lowcmd, publish_state=on_state)
        shim.step()
        self.assertEqual(published_motors, [12])
        self.assertEqual(published_states, [ShimPhase.LYING.value])


if __name__ == "__main__":
    unittest.main()

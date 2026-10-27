"""
Sport shim: serve Go2 sport API in sim via rt/lowcmd (domain 1, interface lo).

Simulation only — never use on real hardware. Move commands time out to zero
velocity after 300 ms without a new Move, matching the sim-serve deadman.
"""

from __future__ import annotations

import json
import math
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from ohho_go2 import sport_api as api
from ohho_go2.dds_guard import assert_sim_dds_only

# Joint order: FR, FL, RR, RL — each (hip, thigh, calf), radians.
NUM_LEG_MOTORS = 12
STAND_POSE: tuple[float, ...] = tuple([0.0, 0.67, -1.3] * 4)
CROUCH_POSE: tuple[float, ...] = tuple([0.0, 1.36, -2.65] * 4)
LYING_POSE: tuple[float, ...] = tuple([0.0, 1.36, -2.65] * 4)

STAND_KP = 60.0
STAND_KD = 5.0
DAMP_KP = 0.0
DAMP_KD = 2.0

# Safety-aligned velocity ceilings (ADR 0001 / SafetyGate defaults).
MAX_LIN_X = 0.5
MAX_LIN_Y = 0.3
MAX_YAW = 1.0
MAX_EULER_RAD = 0.3

# Move stream timeout — zero velocity if no Move for this long (seconds).
# 300 ms matches the console deadman and sim-serve command timeout.
MOVE_COMMAND_TIMEOUT_S = 0.3

RISE_TIME_S = 2.0

LOWCMD_TOPIC = "rt/lowcmd"
LOWSTATE_TOPIC = "rt/lowstate"
SPORT_STATE_TOPIC = "rt/sportmodestate"
SPORT_REQUEST_TOPIC = "rt/api/sport/request"
SPORT_RESPONSE_TOPIC = "rt/api/sport/response"


class ShimPhase(str, Enum):
    LYING = "lying"
    RISING = "rising"
    STANDING = "standing"
    WALKING = "walking"
    SITTING = "sitting"
    DAMPING = "damping"


@dataclass
class MotorCommand:
    q: float = 0.0
    dq: float = 0.0
    kp: float = STAND_KP
    kd: float = STAND_KD
    tau: float = 0.0


@dataclass
class SportModeStateSnapshot:
    """Fields aligned with Unitree SportModeState where practical."""

    mode: int = 0
    progress: float = 0.0
    gait_type: int = 0
    foot_raise_height: float = 0.0
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    velocity: tuple[float, float, float] = (0.0, 0.0, 0.0)
    yaw_speed: float = 0.0
    body_height: float = 0.32
    euler_roll: float = 0.0
    euler_pitch: float = 0.0
    euler_yaw: float = 0.0
    error_code: int = 0
    shim_phase: str = ShimPhase.LYING.value
    policy_stub: bool = True


@dataclass
class SportShimEngine:
    """
    Headless sport shim core: API handling, state machine, lowcmd synthesis.

    Does not open DDS sockets; use :class:`SportShim` for that.
    """

    joint_q: list[float] = field(default_factory=lambda: list(LYING_POSE))
    phase: ShimPhase = ShimPhase.LYING
    rise_start_q: list[float] = field(default_factory=lambda: list(LYING_POSE))
    rise_started_at: float | None = None
    move_vx: float = 0.0
    move_vy: float = 0.0
    move_vyaw: float = 0.0
    last_move_at: float | None = None
    euler_roll: float = 0.0
    euler_pitch: float = 0.0
    euler_yaw: float = 0.0
    latched_estop: bool = False
    policy_stub: bool = True
    checkpoint_path: Path | None = None
    _policy_loaded: bool = False
    _rise_target_phase: ShimPhase = ShimPhase.STANDING
    _time_fn: Callable[[], float] = time.monotonic

    def __post_init__(self) -> None:
        if self.checkpoint_path is not None and self.checkpoint_path.is_file():
            self.policy_stub = not self._try_load_checkpoint(self.checkpoint_path)

    def _try_load_checkpoint(self, path: Path) -> bool:
        """Load RL checkpoint when torch is available; never required in CI."""
        try:
            import torch  # noqa: F401
        except ImportError:
            return False
        try:
            _ = torch.load(path, map_location="cpu", weights_only=True)
        except (OSError, ValueError, TypeError):
            return False
        self._policy_loaded = True
        return True

    def handle_api(self, api_id: int, parameter: str | Mapping[str, Any] | None) -> tuple[int, str]:
        """Handle one sport API request; return (code, message). code 0 = OK."""
        if api_id not in api.SUPPORTED_SPORT_API_IDS:
            return 1, f"unsupported api_id {api_id}"

        if self.latched_estop and api_id not in (
            api.ROBOT_SPORT_API_ID_DAMP,
            api.ROBOT_SPORT_API_ID_STOPMOVE,
        ):
            return 2, "latched e-stop: only StopMove/Damp accepted"

        params = _parse_params(parameter)

        if api_id == api.ROBOT_SPORT_API_ID_DAMP:
            self._enter_damp()
            return 0, "ok"

        if api_id == api.ROBOT_SPORT_API_ID_STOPMOVE:
            self._stop_move(estop=False)
            return 0, "ok"

        if api_id == api.ROBOT_SPORT_API_ID_STANDUP:
            self._begin_rise(target_phase=ShimPhase.STANDING)
            return 0, "ok"

        if api_id == api.ROBOT_SPORT_API_ID_RECOVERYSTAND:
            self._begin_rise(target_phase=ShimPhase.STANDING)
            return 0, "ok"

        if api_id == api.ROBOT_SPORT_API_ID_BALANCESTAND:
            if self.phase in (ShimPhase.LYING, ShimPhase.SITTING, ShimPhase.DAMPING):
                self._begin_rise(target_phase=ShimPhase.STANDING)
            else:
                self.phase = ShimPhase.STANDING
                self.move_vx = self.move_vy = self.move_vyaw = 0.0
            return 0, "ok"

        if api_id == api.ROBOT_SPORT_API_ID_STANDDOWN:
            self._transition_pose(target=LYING_POSE, next_phase=ShimPhase.LYING)
            return 0, "ok"

        if api_id == api.ROBOT_SPORT_API_ID_SIT:
            self._transition_pose(target=CROUCH_POSE, next_phase=ShimPhase.SITTING)
            return 0, "ok"

        if api_id == api.ROBOT_SPORT_API_ID_RISESIT:
            self._begin_rise(target_phase=ShimPhase.STANDING)
            return 0, "ok"

        if api_id == api.ROBOT_SPORT_API_ID_EULER:
            roll = float(params.get("x", params.get("roll", 0.0)))
            pitch = float(params.get("y", params.get("pitch", 0.0)))
            yaw = float(params.get("z", params.get("yaw", 0.0)))
            self.euler_roll = _clamp(roll, -MAX_EULER_RAD, MAX_EULER_RAD)
            self.euler_pitch = _clamp(pitch, -MAX_EULER_RAD, MAX_EULER_RAD)
            self.euler_yaw = _clamp(yaw, -MAX_EULER_RAD, MAX_EULER_RAD)
            if self.phase == ShimPhase.LYING:
                self._begin_rise(target_phase=ShimPhase.STANDING)
            return 0, "ok"

        if api_id == api.ROBOT_SPORT_API_ID_MOVE:
            vx = float(params.get("x", 0.0))
            vy = float(params.get("y", 0.0))
            vyaw = float(params.get("z", 0.0))
            self.move_vx = _clamp(vx, -MAX_LIN_X, MAX_LIN_X)
            self.move_vy = _clamp(vy, -MAX_LIN_Y, MAX_LIN_Y)
            self.move_vyaw = _clamp(vyaw, -MAX_YAW, MAX_YAW)
            now = self._time_fn()
            self.last_move_at = now
            if self.phase in (ShimPhase.STANDING, ShimPhase.WALKING, ShimPhase.RISING):
                if self.phase == ShimPhase.RISING:
                    self.phase = ShimPhase.STANDING
                if abs(self.move_vx) + abs(self.move_vy) + abs(self.move_vyaw) > 1e-6:
                    self.phase = ShimPhase.WALKING
                elif self.phase == ShimPhase.WALKING:
                    self.phase = ShimPhase.STANDING
            elif self.phase in (ShimPhase.LYING, ShimPhase.SITTING, ShimPhase.DAMPING):
                return 3, "Move refused: robot not standing"
            return 0, "ok"

        return 1, "unhandled api"

    def tick(self, dt: float | None = None) -> tuple[list[MotorCommand], SportModeStateSnapshot]:
        """Advance state machine and produce lowcmd + sport state snapshot."""
        now = self._time_fn()
        self._apply_move_timeout(now)
        self._advance_rise(now)

        motors = self._synthesize_lowcmd(dt or 0.002)
        state = self._build_sport_state()
        return motors, state

    def _apply_move_timeout(self, now: float) -> None:
        if self.last_move_at is None:
            return
        if now - self.last_move_at > MOVE_COMMAND_TIMEOUT_S:
            self.move_vx = 0.0
            self.move_vy = 0.0
            self.move_vyaw = 0.0
            if self.phase == ShimPhase.WALKING:
                self.phase = ShimPhase.STANDING

    def _begin_rise(self, target_phase: ShimPhase) -> None:
        self._rise_target_phase = target_phase
        self.rise_start_q = list(self.joint_q)
        self.rise_started_at = self._time_fn()
        self.phase = ShimPhase.RISING

    def _transition_pose(self, target: Sequence[float], next_phase: ShimPhase) -> None:
        self.joint_q = list(target)
        self.phase = next_phase
        self.move_vx = self.move_vy = self.move_vyaw = 0.0
        self.rise_started_at = None

    def _advance_rise(self, now: float) -> None:
        if self.phase != ShimPhase.RISING or self.rise_started_at is None:
            return
        t = now - self.rise_started_at
        s = 0.5 * (1.0 - math.cos(math.pi * min(t / RISE_TIME_S, 1.0)))
        target = STAND_POSE
        for i in range(NUM_LEG_MOTORS):
            self.joint_q[i] = (1.0 - s) * self.rise_start_q[i] + s * target[i]
        if t >= RISE_TIME_S:
            self.joint_q = list(target)
            self.phase = self._rise_target_phase
            self.rise_started_at = None

    def _enter_damp(self) -> None:
        self.phase = ShimPhase.DAMPING
        self.move_vx = self.move_vy = self.move_vyaw = 0.0
        self.latched_estop = True

    def _stop_move(self, estop: bool) -> None:
        self.move_vx = self.move_vy = self.move_vyaw = 0.0
        self.last_move_at = None
        if self.phase == ShimPhase.WALKING:
            self.phase = ShimPhase.STANDING
        if estop:
            self.latched_estop = True

    def _synthesize_lowcmd(self, dt: float) -> list[MotorCommand]:
        if self.phase == ShimPhase.DAMPING:
            return [
                MotorCommand(q=self.joint_q[i], kp=DAMP_KP, kd=DAMP_KD)
                for i in range(NUM_LEG_MOTORS)
            ]

        if self.phase == ShimPhase.WALKING:
            return self._walking_lowcmd(dt)

        target = list(self.joint_q)
        if self.phase in (ShimPhase.STANDING, ShimPhase.RISING):
            target = list(STAND_POSE if self.phase != ShimPhase.RISING else self.joint_q)
        elif self.phase == ShimPhase.SITTING:
            target = list(CROUCH_POSE)
        elif self.phase == ShimPhase.LYING:
            target = list(LYING_POSE)

        return [
            MotorCommand(q=target[i], dq=0.0, kp=STAND_KP, kd=STAND_KD, tau=0.0)
            for i in range(NUM_LEG_MOTORS)
        ]

    def _walking_lowcmd(self, dt: float) -> list[MotorCommand]:
        """RL policy if checkpoint loaded; otherwise honest velocity stub (no fake odometry)."""
        if self._policy_loaded and not self.policy_stub:
            return self._policy_lowcmd(dt)
        return self._stub_walking_lowcmd()

    def _stub_walking_lowcmd(self) -> list[MotorCommand]:
        """PD hold with small hip bias from velocity command — exercises Move path only."""
        bias = 0.04 * self.move_vx + 0.02 * self.move_vy
        yaw_bias = 0.05 * self.move_vyaw
        motors: list[MotorCommand] = []
        for i in range(NUM_LEG_MOTORS):
            q = STAND_POSE[i]
            if i % 3 == 0:
                q += bias + (yaw_bias if i < 6 else -yaw_bias)
            motors.append(MotorCommand(q=q, kp=STAND_KP, kd=STAND_KD))
        return motors

    def _policy_lowcmd(self, dt: float) -> list[MotorCommand]:
        # Placeholder for trained policy inference (OHH-122); falls back to stub.
        return self._stub_walking_lowcmd()

    def _build_sport_state(self) -> SportModeStateSnapshot:
        mode = _phase_to_mode(self.phase)
        gait = 1 if self.phase == ShimPhase.WALKING else 0
        if self.policy_stub and self.phase == ShimPhase.WALKING:
            gait = 255  # reserved: shim stub gait (not a real Unitree gait id)
        return SportModeStateSnapshot(
            mode=mode,
            progress=_rise_progress(self),
            gait_type=gait,
            velocity=(self.move_vx, self.move_vy, 0.0),
            yaw_speed=self.move_vyaw,
            euler_roll=self.euler_roll,
            euler_pitch=self.euler_pitch,
            euler_yaw=self.euler_yaw,
            error_code=1 if self.latched_estop else 0,
            shim_phase=self.phase.value,
            policy_stub=self.policy_stub or not self._policy_loaded,
        )


class SportShim:
    """
    DDS-facing sport shim (domain 1, ``lo`` only).

    Subscribes to sport API requests and publishes lowcmd + SportModeState.
    """

    def __init__(
        self,
        domain: int = 1,
        interface: str = "lo",
        checkpoint: str | Path | None = None,
        engine: SportShimEngine | None = None,
    ) -> None:
        assert_sim_dds_only(domain, interface)
        self.domain = domain
        self.interface = interface
        ckpt = Path(checkpoint) if checkpoint else None
        self.engine = engine or SportShimEngine(checkpoint_path=ckpt)
        self._connected = False
        self._publish_lowcmd: Callable[[list[MotorCommand]], None] | None = None
        self._publish_state: Callable[[SportModeStateSnapshot], None] | None = None
        self._publish_response: Callable[[int, int, str], None] | None = None

    def connect(
        self,
        publish_lowcmd: Callable[[list[MotorCommand]], None] | None = None,
        publish_state: Callable[[SportModeStateSnapshot], None] | None = None,
        publish_response: Callable[[int, int, str], None] | None = None,
    ) -> None:
        """Initialize DDS (when SDK present) and optional injectable publishers."""
        assert_sim_dds_only(self.domain, self.interface)
        try:
            from unitree_sdk2py.core.channel import ChannelFactoryInitialize

            ChannelFactoryInitialize(self.domain, self.interface)
        except ImportError:
            pass
        self._publish_lowcmd = publish_lowcmd
        self._publish_state = publish_state
        self._publish_response = publish_response
        self._connected = True

    def on_sport_request(self, api_id: int, request_id: int, parameter: str) -> None:
        code, msg = self.engine.handle_api(api_id, parameter)
        if self._publish_response is not None:
            self._publish_response(request_id, api_id, json.dumps({"code": code, "message": msg}))

    def step(self, dt: float = 0.002) -> tuple[list[MotorCommand], SportModeStateSnapshot]:
        motors, state = self.engine.tick(dt)
        if self._publish_lowcmd is not None:
            self._publish_lowcmd(motors)
        if self._publish_state is not None:
            self._publish_state(state)
        return motors, state


def _parse_params(parameter: str | Mapping[str, Any] | None) -> dict[str, Any]:
    if parameter is None:
        return {}
    if isinstance(parameter, Mapping):
        return dict(parameter)
    text = parameter.strip()
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    if isinstance(data, dict):
        return data
    return {}


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _phase_to_mode(phase: ShimPhase) -> int:
    return {
        ShimPhase.LYING: 7,
        ShimPhase.RISING: 4,
        ShimPhase.STANDING: 1,
        ShimPhase.WALKING: 2,
        ShimPhase.SITTING: 6,
        ShimPhase.DAMPING: 0,
    }.get(phase, 0)


def _rise_progress(engine: SportShimEngine) -> float:
    if engine.phase != ShimPhase.RISING or engine.rise_started_at is None:
        return 1.0 if engine.phase != ShimPhase.RISING else 0.0
    t = engine._time_fn() - engine.rise_started_at
    return _clamp(t / RISE_TIME_S, 0.0, 1.0)

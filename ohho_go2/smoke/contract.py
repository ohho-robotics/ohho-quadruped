"""
Behavior contract exercised by CI smoke tests (OHH-124).

Pure Python — no unitree_sdk2py or DDS imports. Mirrors planned SafetyGate /
sport-shim limits from AGENTS.md and ADR 0001.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Protocol

DEFAULT_MAX_LINEAR_M_S = 0.5
DEFAULT_MAX_LATERAL_M_S = 0.3
DEFAULT_MAX_YAW_RAD_S = 1.0
WALK_TEST_VELOCITY_M_S = 0.3
WALK_TEST_DURATION_S = 5.0
COMMAND_WATCHDOG_S = 0.3


@dataclass(frozen=True)
class SimDdsConfig:
    domain_id: int = 1
    interface: str = "lo"


def validate_sim_dds(config: SimDdsConfig) -> None:
    if config.domain_id != 1:
        raise ValueError(f"sim must use DDS domain 1, got {config.domain_id}")
    if config.interface != "lo":
        raise ValueError(f"sim must use loopback interface lo, got {config.interface!r}")


def clamp_linear_speed(requested_m_s: float, max_lin: float = DEFAULT_MAX_LINEAR_M_S) -> float:
    if requested_m_s < 0:
        raise ValueError("linear speed must be non-negative")
    return min(requested_m_s, max_lin)


def refuse_hardware_connect(uri: str, armed: bool, is_tty: bool) -> None:
    """Fail closed for hardware URIs unless explicitly armed from an interactive TTY."""
    if uri.startswith("sim://") or uri.startswith("mujoco://"):
        return
    if "lo" in uri and "domain=1" in uri:
        return
    if not armed:
        raise PermissionError("hardware connect refused: OHHO_ARM_HARDWARE not set")
    if not is_tty:
        raise PermissionError("hardware connect refused: interactive TTY confirmation required")


class RobotClient(Protocol):
    connected: bool
    position_x_m: float
    estop_latched: bool

    def connect(self, uri: str) -> None: ...

    def stand_up(self) -> None: ...

    def move(self, vx_m_s: float, vy_m_s: float, vyaw_rad_s: float) -> None: ...

    def stop_move(self) -> None: ...

    def trigger_estop(self) -> None: ...


@dataclass
class MockRobotClient:
    """In-memory robot double for unittest smoke scenarios."""

    connected: bool = False
    position_x_m: float = 0.0
    last_vx_m_s: float = 0.0
    estop_latched: bool = False
    standing: bool = False
    _last_command_monotonic: float = field(default_factory=time.monotonic)

    def connect(self, uri: str) -> None:
        refuse_hardware_connect(uri, armed=False, is_tty=False)
        validate_sim_dds(SimDdsConfig())
        self.connected = True

    def stand_up(self) -> None:
        if not self.connected:
            raise RuntimeError("not connected")
        if self.estop_latched:
            raise RuntimeError("e-stop latched")
        self.standing = True
        self._touch_command()

    def move(self, vx_m_s: float, vy_m_s: float, vyaw_rad_s: float) -> None:
        if not self.connected:
            raise RuntimeError("not connected")
        if self.estop_latched:
            raise RuntimeError("e-stop latched")
        vx_m_s = clamp_linear_speed(vx_m_s)
        self.last_vx_m_s = vx_m_s
        self._touch_command()
        # Integrate forward motion for delta-x checks (vy/vyaw ignored in mock).
        self.position_x_m += vx_m_s * 0.05

    def stop_move(self) -> None:
        self.last_vx_m_s = 0.0
        self._touch_command()

    def trigger_estop(self) -> None:
        self.estop_latched = True
        self.stop_move()

    def tick_watchdog(self, idle_s: float) -> None:
        if not self.connected:
            return
        if time.monotonic() - self._last_command_monotonic >= idle_s:
            self.last_vx_m_s = 0.0

    def _touch_command(self) -> None:
        self._last_command_monotonic = time.monotonic()


class SmokeScenarios:
    def __init__(self, client: RobotClient) -> None:
        self._client = client

    def connect_sim(self, uri: str = "sim://go2/domain=1/lo") -> None:
        self._client.connect(uri)

    def stand(self) -> None:
        self._client.stand_up()

    def walk_forward(
        self,
        speed_m_s: float = WALK_TEST_VELOCITY_M_S,
        duration_s: float = WALK_TEST_DURATION_S,
    ) -> float:
        applied = clamp_linear_speed(speed_m_s)
        start_x = self._client.position_x_m
        steps = max(1, int(duration_s / 0.05))
        for _ in range(steps):
            self._client.move(applied, 0.0, 0.0)
        return self._client.position_x_m - start_x

    def request_speed_clamped(self, requested_m_s: float) -> float:
        applied = clamp_linear_speed(requested_m_s)
        self._client.move(applied, 0.0, 0.0)
        return applied

    def watchdog_zeros_velocity_after_idle(self, idle_s: float = COMMAND_WATCHDOG_S) -> float:
        self._client.move(WALK_TEST_VELOCITY_M_S, 0.0, 0.0)
        if isinstance(self._client, MockRobotClient):
            self._client._last_command_monotonic = time.monotonic() - idle_s - 0.01
            self._client.tick_watchdog(idle_s)
        return self._client.last_vx_m_s

    def estop_latches(self) -> None:
        self._client.trigger_estop()
        if not self._client.estop_latched:
            raise AssertionError("e-stop did not latch")

"""300 ms cmd_vel watchdog → StopMove (matches SafetyGate / sim deadman)."""

from __future__ import annotations

import math
from dataclasses import dataclass

DEFAULT_WATCHDOG_SEC = 0.3


def require_positive_finite_timeout(
    timeout_s: float,
    *,
    name: str = "watchdog_timeout_sec",
) -> float:
    """Reject NaN, infinities, zero, and negative watchdog periods."""
    if not math.isfinite(timeout_s) or timeout_s <= 0.0:
        raise ValueError(f"{name} must be finite and > 0, got {timeout_s!r}")
    return float(timeout_s)


@dataclass
class CmdVelWatchdog:
    """Tracks last cmd_vel time; signals when StopMove should be sent."""

    timeout_sec: float = DEFAULT_WATCHDOG_SEC
    last_cmd_monotonic: float | None = None

    def record_cmd(self, now_monotonic: float) -> None:
        self.last_cmd_monotonic = now_monotonic

    def should_stop_move(self, now_monotonic: float) -> bool:
        if self.last_cmd_monotonic is None:
            return False
        return (now_monotonic - self.last_cmd_monotonic) > self.timeout_sec

    def clear(self) -> None:
        self.last_cmd_monotonic = None

"""Pure-Python /cmd_vel handling (clamp + watchdog); used by the ROS node and tests."""

from __future__ import annotations

from ohho_go2_bridge.transport import SportTransport
from ohho_go2_bridge.velocity_limits import clamp_twist
from ohho_go2_bridge.watchdog import CmdVelWatchdog


class CmdVelBridge:
    def __init__(
        self,
        transport: SportTransport,
        watchdog: CmdVelWatchdog | None = None,
    ) -> None:
        self._transport = transport
        self._watchdog = watchdog or CmdVelWatchdog()

    @property
    def watchdog(self) -> CmdVelWatchdog:
        return self._watchdog

    def on_cmd_vel(
        self,
        linear_x: float,
        linear_y: float,
        angular_z: float,
        now_monotonic: float,
    ) -> bool:
        """Apply clamped Move; return True if any component was clamped."""
        lx, ly, az, clamped = clamp_twist(linear_x, linear_y, angular_z)
        self._transport.move(lx, ly, az)
        self._watchdog.record_cmd(now_monotonic)
        return clamped

    def tick_watchdog(self, now_monotonic: float) -> bool:
        """Send StopMove when the watchdog fires; return True if sent."""
        if self._watchdog.should_stop_move(now_monotonic):
            self._transport.stop_move()
            self._watchdog.clear()
            return True
        return False

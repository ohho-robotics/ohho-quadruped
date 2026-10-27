"""Pure kinematic model for the sim-only Nav2 sensor node. Not a hardware model."""

from __future__ import annotations

import math
from dataclasses import dataclass

GO2_JOINT_NAMES = [
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
]
GO2_STAND_POSITIONS = [0.0, 0.8, -1.5] * 4

ROOM_HALF_M = 3.0
SCAN_READINGS = 180
SCAN_ANGLE_MIN = -math.pi
SCAN_ANGLE_MAX = math.pi
SCAN_RANGE_MIN_M = 0.1
SCAN_RANGE_MAX_M = 20.0
DEFAULT_WATCHDOG_SEC = 0.3


@dataclass
class SimKinematics:
    """Integrate body-frame velocity inside a rectangular room."""

    x: float = 0.0
    y: float = 0.0
    yaw: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    vyaw: float = 0.0
    last_cmd_s: float | None = None
    last_tick_s: float | None = None

    def set_body_velocity(self, vx: float, vy: float, vyaw: float, now_s: float) -> None:
        self.vx = vx
        self.vy = vy
        self.vyaw = vyaw
        self.last_cmd_s = now_s

    def apply_cmd_timeout(self, now_s: float, timeout_s: float = DEFAULT_WATCHDOG_SEC) -> bool:
        """Zero body velocity after cmd_vel has been silent for timeout_s."""
        if self.last_cmd_s is None or now_s - self.last_cmd_s <= timeout_s:
            return False
        if self.vx == 0.0 and self.vy == 0.0 and self.vyaw == 0.0:
            return False
        self.vx = 0.0
        self.vy = 0.0
        self.vyaw = 0.0
        return True

    def integrate(self, now_s: float, dt_cap_s: float = 0.5) -> float:
        if self.last_tick_s is None:
            self.last_tick_s = now_s
            return 0.0
        dt = min(max(now_s - self.last_tick_s, 0.0), dt_cap_s)
        self.last_tick_s = now_s
        cos_yaw = math.cos(self.yaw)
        sin_yaw = math.sin(self.yaw)
        self.x += (self.vx * cos_yaw - self.vy * sin_yaw) * dt
        self.y += (self.vx * sin_yaw + self.vy * cos_yaw) * dt
        self.yaw += self.vyaw * dt
        return dt

    def yaw_quaternion(self) -> tuple[float, float]:
        return math.sin(self.yaw / 2.0), math.cos(self.yaw / 2.0)

    def scan_ranges(self) -> list[float]:
        return room_scan_ranges(self.x, self.y, self.yaw)


def room_scan_ranges(
    x: float,
    y: float,
    yaw: float,
    *,
    num_readings: int = SCAN_READINGS,
    room_half: float = ROOM_HALF_M,
    range_min: float = SCAN_RANGE_MIN_M,
    range_max: float = SCAN_RANGE_MAX_M,
) -> list[float]:
    """Distance to the walls of a square room, in the sensor frame plus yaw."""
    angle_increment = (SCAN_ANGLE_MAX - SCAN_ANGLE_MIN) / num_readings
    ranges: list[float] = []
    for i in range(num_readings):
        angle = SCAN_ANGLE_MIN + i * angle_increment + yaw
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        distance = range_max
        if abs(cos_a) > 1e-3:
            dx = (room_half - x if cos_a > 0 else -room_half - x) / cos_a
            if dx > 0:
                distance = min(distance, dx)
        if abs(sin_a) > 1e-3:
            dy = (room_half - y if sin_a > 0 else -room_half - y) / sin_a
            if dy > 0:
                distance = min(distance, dy)
        ranges.append(max(range_min, min(range_max, distance)))
    return ranges

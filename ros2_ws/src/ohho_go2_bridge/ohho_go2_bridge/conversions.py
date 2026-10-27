"""
Message conversion helpers (stdlib-only shapes for tests).

Unitree SportModeState / LowState / lidar cloud adapters will plug in when
unitree_ros2 is available; until then these document field mapping.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SportModeSnapshot:
    """Minimal fields needed for nav_msgs/Odometry + TF."""

    x: float
    y: float
    z: float
    yaw: float
    vx: float
    vy: float
    vyaw: float


@dataclass(frozen=True)
class LowStateSnapshot:
    """Minimal fields for sensor_msgs/JointState and battery."""

    joint_names: tuple[str, ...]
    joint_positions: tuple[float, ...]
    battery_soc_percent: float


def sport_to_odom_fields(state: SportModeSnapshot) -> dict[str, float]:
    """Map sport mode state into odometry pose/twist scalars (planar)."""
    return {
        "pose_x": state.x,
        "pose_y": state.y,
        "pose_z": state.z,
        "yaw": state.yaw,
        "twist_vx": state.vx,
        "twist_vy": state.vy,
        "twist_vyaw": state.vyaw,
    }


def lowstate_to_joint_battery(state: LowStateSnapshot) -> tuple[tuple[str, ...], float]:
    return state.joint_names, state.battery_soc_percent

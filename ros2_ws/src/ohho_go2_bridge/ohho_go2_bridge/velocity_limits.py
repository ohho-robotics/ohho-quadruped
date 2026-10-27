"""Velocity caps aligned with planned SafetyGate defaults (ADR 0001 / AGENTS.md)."""

from __future__ import annotations

import math
from dataclasses import dataclass

# Go2 defaults (m/s and rad/s).
DEFAULT_MAX_FORWARD_MPS = 0.5
DEFAULT_MAX_LATERAL_MPS = 0.3
DEFAULT_MAX_YAW_RADPS = 1.0

# Spec hard ceilings (config-only raise in future SafetyGate).
CEILING_MAX_LINEAR_MPS = 1.5
CEILING_MAX_YAW_RADPS = 2.0


@dataclass(frozen=True)
class VelocityCaps:
    max_forward_mps: float = DEFAULT_MAX_FORWARD_MPS
    max_lateral_mps: float = DEFAULT_MAX_LATERAL_MPS
    max_yaw_radps: float = DEFAULT_MAX_YAW_RADPS
    ceiling_linear_mps: float = CEILING_MAX_LINEAR_MPS
    ceiling_yaw_radps: float = CEILING_MAX_YAW_RADPS


def _clamp_symmetric(value: float, limit: float) -> float:
    # NaN fails both comparisons and would otherwise pass through to Move.
    if math.isnan(value):
        return 0.0
    if value > limit:
        return limit
    if value < -limit:
        return -limit
    return value


def clamp_twist(
    linear_x: float,
    linear_y: float,
    angular_z: float,
    caps: VelocityCaps | None = None,
) -> tuple[float, float, float, bool]:
    """
    Clamp cmd_vel components to SafetyGate-style caps.

    Returns (lx, ly, az, was_clamped).
    """
    caps = caps or VelocityCaps()

    eff_fwd = min(caps.max_forward_mps, caps.ceiling_linear_mps)
    eff_lat = min(caps.max_lateral_mps, caps.ceiling_linear_mps)
    eff_yaw = min(caps.max_yaw_radps, caps.ceiling_yaw_radps)

    lx = _clamp_symmetric(linear_x, eff_fwd)
    ly = _clamp_symmetric(linear_y, eff_lat)
    az = _clamp_symmetric(angular_z, eff_yaw)

    clamped = (lx, ly, az) != (linear_x, linear_y, angular_z)
    return lx, ly, az, clamped

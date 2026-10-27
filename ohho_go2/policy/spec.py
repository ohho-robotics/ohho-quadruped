"""Velocity policy observation/action contract and config validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

OBS_DIM = 48
ACTION_DIM = 12

JOINT_NAMES = (
    "FR_hip",
    "FR_thigh",
    "FR_calf",
    "FL_hip",
    "FL_thigh",
    "FL_calf",
    "RR_hip",
    "RR_thigh",
    "RR_calf",
    "RL_hip",
    "RL_thigh",
    "RL_calf",
)

OBS_BLOCKS = (
    ("base_lin_vel", 3, 2.0),
    ("base_ang_vel", 3, 0.25),
    ("projected_gravity", 3, 1.0),
    ("cmd_vel", 3, 1.0),
    ("joint_pos_rel", 12, 1.0),
    ("joint_vel", 12, 0.05),
    ("last_action", 12, 1.0),
)


@dataclass(frozen=True)
class VelocityPolicySpec:
    """Frozen spec shared by train configs and export manifest."""

    spec_version: str
    terrain: str
    cmd_vel_limits: dict[str, float]
    default_joint_pos: tuple[float, ...]
    action_scale: float
    policy_hz: float
    kp: tuple[float, ...]
    kd: tuple[float, ...]
    obs_dim: int = OBS_DIM
    action_dim: int = ACTION_DIM

    def validate(self) -> None:
        if self.obs_dim != OBS_DIM:
            raise ValueError(f"obs_dim must be {OBS_DIM}, got {self.obs_dim}")
        if self.action_dim != ACTION_DIM:
            raise ValueError(f"action_dim must be {ACTION_DIM}, got {self.action_dim}")
        if len(self.default_joint_pos) != ACTION_DIM:
            raise ValueError("default_joint_pos must have 12 elements")
        if len(self.kp) != ACTION_DIM or len(self.kd) != ACTION_DIM:
            raise ValueError("kp and kd must have 12 elements each")
        for key in ("vx", "vy", "wz"):
            if key not in self.cmd_vel_limits:
                raise ValueError(f"cmd_vel_limits missing {key}")
        expected = sum(block[1] for block in OBS_BLOCKS)
        if expected != OBS_DIM:
            raise ValueError("OBS_BLOCKS sum mismatch")

    @property
    def obs_block_offsets(self) -> list[tuple[str, int, int, float]]:
        offset = 0
        out: list[tuple[str, int, int, float]] = []
        for name, dim, scale in OBS_BLOCKS:
            out.append((name, offset, offset + dim, scale))
            offset += dim
        return out


def _parse_spec(data: dict[str, Any]) -> VelocityPolicySpec:
    spec = VelocityPolicySpec(
        spec_version=str(data["spec_version"]),
        terrain=str(data["terrain"]),
        cmd_vel_limits={k: float(v) for k, v in data["cmd_vel_limits"].items()},
        default_joint_pos=tuple(float(x) for x in data["default_joint_pos"]),
        action_scale=float(data["action_scale"]),
        policy_hz=float(data["policy_hz"]),
        kp=tuple(float(x) for x in data["kp"]),
        kd=tuple(float(x) for x in data["kd"]),
        obs_dim=int(data.get("obs_dim", OBS_DIM)),
        action_dim=int(data.get("action_dim", ACTION_DIM)),
    )
    spec.validate()
    return spec


def load_spec_from_config(path: Path | str) -> VelocityPolicySpec:
    raw = Path(path).read_text(encoding="utf-8")
    return _parse_spec(json.loads(raw))


def config_dir() -> Path:
    return Path(__file__).resolve().parent / "config"

"""Locate a pinned unitree_mujoco checkout."""

from __future__ import annotations

import os
from pathlib import Path

from sim.pins import UNITREE_MUJOCO_REF


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def resolve_unitree_mujoco_root() -> Path:
    override = os.environ.get("OHHO_UNITREE_MUJOCO_ROOT")
    if override:
        root = Path(override).expanduser()
    else:
        unitree_ws = Path(os.environ.get("UNITREE_WS", Path.home() / "unitree")).expanduser()
        root = unitree_ws / "unitree_mujoco"
    if not root.is_dir():
        raise FileNotFoundError(
            f"unitree_mujoco not found at {root}. "
            "Run scripts/dev/setup-unitree-wsl.sh or set OHHO_UNITREE_MUJOCO_ROOT."
        )
    return root


def go2_robot_dir(unitree_mujoco_root: Path) -> Path:
    return unitree_mujoco_root / "unitree_robots" / "go2"


def simulate_python_dir(unitree_mujoco_root: Path) -> Path:
    return unitree_mujoco_root / "simulate_python"


def read_checkout_ref(unitree_mujoco_root: Path) -> str | None:
    git_dir = unitree_mujoco_root / ".git"
    if not git_dir.exists():
        return None
    import subprocess

    try:
        out = subprocess.run(
            ["git", "-C", str(unitree_mujoco_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return out.stdout.strip()


def assert_pinned_ref(unitree_mujoco_root: Path, *, strict: bool = False) -> None:
    head = read_checkout_ref(unitree_mujoco_root)
    if head is None:
        return
    if head != UNITREE_MUJOCO_REF:
        msg = (
            f"unitree_mujoco at {unitree_mujoco_root} is at {head}, "
            f"expected pin {UNITREE_MUJOCO_REF}"
        )
        if strict:
            raise RuntimeError(msg)
        import warnings

        warnings.warn(msg, stacklevel=2)

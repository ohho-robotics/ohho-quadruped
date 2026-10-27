"""
ohho_go2 — sport shim and sim helpers for the OhhO Quadruped (Unitree Go2, sim only).

The sport shim serves the Go2 sport API on DDS domain 1 / interface ``lo`` and
translates commands into ``rt/lowcmd`` for unitree_mujoco. It is not for hardware.
"""

from ohho_go2.sport_shim import SportShim, SportShimEngine

__all__ = ["SportShim", "SportShimEngine", "__version__"]
__version__ = "0.0.0"

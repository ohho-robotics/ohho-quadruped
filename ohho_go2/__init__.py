"""
ohho_go2 — planned package for the OhhO Quadruped sport shim and sim helpers.

Status: planned, not built.

This package will hold:
- A sport-mode shim that translates the ohho-sdk Sport API into
  unitree_mujoco low-level commands (LowCmd over DDS domain 1, interface lo).
- Sim helpers and scene descriptions for unitree_mujoco.

Implementation starts in November per ADR 0001 (proposed, PR #3):
https://github.com/ohho-robotics/ohho-quadruped/pull/3

Nothing in this module is implemented or executable today.
Do not add runtime imports of unitree_sdk2py or DDS code to this package
until M1/M2 work begins in November.
"""

__version__ = "0.0.0"

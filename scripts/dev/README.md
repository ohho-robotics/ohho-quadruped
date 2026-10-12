# scripts/dev/ — planned, not built

**Status: planned. Nothing in this directory is implemented.**

This directory will hold dev-environment helper scripts, for example:

- `setup-wsl2.sh` — install CycloneDDS 0.10.2, unitree_sdk2_python, and
  unitree_mujoco in WSL2 Ubuntu 22.04 (OHH-114)
- `check-dds.sh` — verify DDS domain 1 / lo is reachable inside WSL2

These scripts target WSL2 only. They are not needed on the robot or in CI.

## Implementation schedule

M0 dev-env setup (OHH-114, October 2026) per ADR 0001 (proposed, PR #3):
https://github.com/ohho-robotics/ohho-quadruped/pull/3

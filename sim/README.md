# sim/ — planned, not built

**Status: planned. Nothing in this directory is implemented.**

This directory will hold:

- `launch/` — unitree_mujoco launch scripts for the Go2 scene
- `scenes/` — MuJoCo XML scene descriptions (Go2 robot + environment)

## Planned setup

The simulator uses `unitree_mujoco` (Python) on **DDS domain 1, interface `lo`**
(loopback). This is the default for sim. Domain 0 or a real NIC requires the
hardware-arming flag (`OHHO_ARM_HARDWARE=1`) and an interactive TTY confirmation
that a human operator is physically present — agents and CI cannot arm.

Switching from sim to real is a one-line change:
`ChannelFactoryInitialize(1, "lo")` → `ChannelFactoryInitialize(0, "<nic>")`.

## Dependencies (planned)

- `unitree_mujoco` (installed from source in WSL2 Ubuntu 22.04, OHH-114)
- MuJoCo viewer via WSLg
- CycloneDDS 0.10.2 (pinned)
- DDS domain 1 / interface `lo` for sim

ROS 2, Gazebo, Isaac, and GPU tooling are **not** used in this directory.

## Implementation schedule

M2 (November 2026, OHH-121–124) per ADR 0001 (proposed, PR #3):
https://github.com/ohho-robotics/ohho-quadruped/pull/3

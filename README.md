# OhhO Quadruped

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Sim smoke CI](https://img.shields.io/badge/sim%20smoke-workflow-blue)](.github/workflows/sim-smoke.yml)

**M0 scaffold — no robot code yet.** The working robot is [OmniBot](https://github.com/ohho-robotics/OmniBot).

This repository is the scaffold for a quadruped form factor in the
[OhhO Robotics](https://github.com/ohho-robotics) org.
Implementation starts in November 2026 per ADR 0001:
https://github.com/ohho-robotics/ohho-quadruped/pull/3

## Status

| Item | Status | Evidence |
|---|---|---|
| Credibility check v2 | Built | [scripts/check_credibility.py](scripts/check_credibility.py), [.github/workflows/credibility.yml](.github/workflows/credibility.yml) |
| Python lint + unittest CI | Built | [.github/workflows/python.yml](.github/workflows/python.yml) |
| Go2 velocity policy train/export scaffold (OHH-122) | Built | [docs/train-velocity-policy.md](docs/train-velocity-policy.md), [ohho_go2/policy/](ohho_go2/policy/), [.github/workflows/python.yml](.github/workflows/python.yml) |
| MuJoCo + DDS smoke CI (OHH-124) | In progress | [.github/workflows/sim-smoke.yml](.github/workflows/sim-smoke.yml) |
| Sim quickstart (in-process) | Built | [.github/workflows/credibility.yml](.github/workflows/credibility.yml) |
| AGENTS.md safety rules for coding agents | Built | [AGENTS.md](AGENTS.md), [.github/workflows/credibility.yml](.github/workflows/credibility.yml) |
| Decision record ADR 0001 (accepted) | Built | [docs/adr/0001-unitree-go2.md](docs/adr/0001-unitree-go2.md), [.github/workflows/credibility.yml](.github/workflows/credibility.yml), https://github.com/ohho-robotics/ohho-quadruped/pull/3 |
| Dev environment on Varun's PC (OHH-114) | In progress | [docs/dev-setup.md](docs/dev-setup.md), https://linear.app/ohho-robotics/issue/OHH-114 |
| Unitree Go2 EDU in MuJoCo sim (unitree_mujoco, sport shim) | Vision | planned, from November 2026 |
| ROS 2 bridge (Humble, Jazzy best-effort) | In progress | [ros2_ws/src/ohho_go2_bridge/](ros2_ws/src/ohho_go2_bridge/), [.github/workflows/ros2-bridge.yml](.github/workflows/ros2-bridge.yml) |
| Go2 description + RViz + Nav2 params (OHH-132) | In progress | [ros2_ws/src/go2_description/](ros2_ws/src/go2_description/), [ros2_ws/src/ohho_go2_navigation/](ros2_ws/src/ohho_go2_navigation/) |
| Hardware bring-up (Go2 EDU, operator present) | Vision | Vision until Go2 EDU available |

## Sim only, not hardware-tested

Nothing in this repository has been tested on hardware.
No hardware commands are run from any agent session.
Hardware bring-up is gated on a physical Go2 EDU and an operator being present (OHH-135).

### Quickstart (sim)

In-process CPU simulation via `ohho-os` (no hardware required):

```bash
pip install ohho-os
ohho doctor
ohho sim --robot unitree-go2 --seconds 2
```

This exercises the simulated quadruped kinematics and telemetry without connecting to real hardware.
For full MuJoCo simulation setup in WSL2 Ubuntu 22.04 (OHH-114), see [docs/dev-setup.md](docs/dev-setup.md).

## Clone

```bash
git clone https://github.com/ohho-robotics/ohho-quadruped.git
```

## Checks

```bash
python -m unittest discover -s tests
```

```bash
ruff check .
```

```bash
bash scripts/check-credibility.sh
```

## Layout

```text
ohho_go2/                         Python package: sport shim + sim helpers (planned, November 2026); policy scaffold (OHH-122)
sim/                              Go2 sim launcher + OhhO scenes (see sim/README.md)
ros2_ws/src/ohho_go2_bridge/      ROS 2 Humble bridge (scaffold; mock transport)
ros2_ws/src/go2_description/      Go2 URDF, meshes, and RViz display launch
ros2_ws/src/ohho_go2_navigation/  Nav2 params, SLAM toolbox, sim-only sensors, and all-in-one sim launch
docs/                             ADRs, runbooks, and sibling follow-ups (ADR 0001 accepted; ADR 0002 velocity-policy scaffold)
scripts/                          Credibility check v2
tests/                            stdlib unittest tests
```

## License

[Apache License 2.0](LICENSE).

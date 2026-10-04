# OhhO Quadruped

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

**M0 scaffold — no robot code yet.** The working robot is [OmniBot](https://github.com/ohho-robotics/OmniBot).

This repository is the scaffold for a quadruped form factor in the
[OhhO Robotics](https://github.com/ohho-robotics) org.
Implementation starts in November 2026 per ADR 0001 (proposed, PR #3):
https://github.com/ohho-robotics/ohho-quadruped/pull/3

## Status

| Item | Status | Evidence |
|---|---|---|
| Credibility check v2 | Built | [scripts/check_credibility.py](scripts/check_credibility.py), [.github/workflows/credibility.yml](.github/workflows/credibility.yml) |
| Python lint + unittest CI | Built | [.github/workflows/python.yml](.github/workflows/python.yml) |
| AGENTS.md safety rules for coding agents | Built | [AGENTS.md](AGENTS.md) |
| Decision record ADR 0001 (proposed) | In progress | https://github.com/ohho-robotics/ohho-quadruped/pull/3 |
| Dev environment on Varun's PC (OHH-114) | In progress | https://linear.app/ohho-robotics/issue/OHH-114 |
| Unitree Go2 EDU in MuJoCo sim (unitree_mujoco, sport shim) | Vision | planned, from November 2026 |
| ROS 2 bridge (Humble, Jazzy best-effort) | Vision | planned, from early 2027 |
| Hardware bring-up (gated on a Go2 EDU, operator present) | Vision | planned, gated on OHH-135 |

## Sim only, not hardware-tested

Nothing in this repository has been tested on hardware.
No hardware commands are run from any agent session.
Hardware bring-up is gated on a physical Go2 EDU and an operator being present (OHH-135).

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
ohho_go2/          Python package: sport shim + sim helpers (planned, November 2026)
sim/               unitree_mujoco launch + scenes (planned, November 2026)
ros2_ws/src/ohho_go2_bridge/   ROS 2 Humble bridge (planned, early 2027)
docs/              ADRs and runbooks (ADR 0001 in PR #3)
scripts/           Credibility check v2
tests/             stdlib unittest tests
```

## License

[Apache License 2.0](LICENSE).

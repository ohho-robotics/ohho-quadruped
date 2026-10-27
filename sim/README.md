# sim/ — Go2 MuJoCo launcher (OHH-121)

OhhO scenes and a launcher around Unitree's pinned `unitree_mujoco` Python sim
(`simulate_python`) on **DDS domain 1, interface `lo`**.

## Prerequisites

Install the pinned stack in WSL2 Ubuntu 22.04 (OHH-114):

```bash
bash scripts/dev/setup-unitree-wsl.sh
. ~/unitree/env.sh
```

Pin: `1eb6642e3f3fdfb7fb13a9794fd6a2dd93ea0e7d` (see `sim/pins.py` and `NOTICE`).

Override checkout location:

```bash
export OHHO_UNITREE_MUJOCO_ROOT=~/unitree/unitree_mujoco
```

## Run

From the repo root (with `env.sh` sourced in WSL):

```bash
python sim/run_go2.py --scene flat
python sim/run_go2.py --headless --scene office --no-joystick
python sim/run_go2.py --headless --scene flat --render-front-camera --duration 10
```

| Flag | Default | Purpose |
|------|---------|---------|
| `--scene` | `flat` | `flat`, `terrain`, or `office` |
| `--headless` | off | No viewer; set `MUJOCO_GL=egl` (or `osmesa`) for offscreen |
| `--domain` | `1` | CycloneDDS domain |
| `--iface` | `lo` | DDS interface (loopback for sim) |
| `--no-joystick` | off | Disable wireless controller emulation |
| `--render-front-camera` | off | Offscreen render `ohho_front_camera` each step |

Headless CI should use EGL or OSMesa (`MUJOCO_GL=egl` or `MUJOCO_GL=osmesa`), not Xvfb.

## Scenes

- `sim/scenes/*_env.xml` — environment MJCF fragments (floor, props).
- Composed with `unitree_robots/go2/go2.xml` from the pinned `unitree_mujoco` tree.
- Labelled objects (`red_box`, `blue_cone`, …) have fixed world poses in
  `sim/scene_objects.py` for perception / nav tests later.
- `ohho_front_camera` is attached to `base_link` at the Go2 head pose when the
  model is loaded (see `sim/mjcf.py`).

## Layout

```text
sim/run_go2.py       CLI entry
sim/launcher.py      DDS + physics loop (viewer or headless)
sim/mjcf.py          Scene compose + front camera
sim/scenes/          OhhO MJCF environment fragments
```

## Safety

Domain 0 or a non-loopback interface requires `OHHO_ARM_HARDWARE=1` and an
interactive TTY confirmation. Agents and CI must stay on domain 1 / `lo`.

## Verification (human / CI)

- `python sim/run_go2.py --headless --scene office` for 60 s at real-time factor
  ≥ 0.9 with LowState on domain 1 — not automated in this repo yet; see OHH-121
  acceptance criteria.

Smoke of the upstream stack (without OhhO scenes):

```bash
bash scripts/dev/smoke-unitree-sim.sh
```

## Local /sim stack

`scripts/dev/sim-go2-stack.sh` starts three processes on DDS domain 1 / `lo`:

1. `python sim/run_go2.py --headless --no-joystick --domain 1 --iface lo` (MuJoCo)
2. `python -m ohho_go2.dds_server` (sport RPC + `rt/lowcmd`)
3. `ohho sim-serve --backend robot --robot unitree-go2 --transport dds://lo?domain=1`

Point `OHHO_OS` at an ohho-os checkout and source the Unitree env (the script
does that when `UNITREE_ENV` is set; default `/opt/unitree/env.sh`). sim-serve
listens on `ws://127.0.0.1:8765`. The console Add robot → Go2 → Simulation
page connects there. The in-browser kinematic sim stays the fallback when
nothing is listening.

```bash
export OHHO_OS=/path/to/ohho-os
bash scripts/dev/sim-go2-stack.sh
```

The Unitree venv also needs `websockets` (`pip install websockets`). Do not
change the domain or interface: the sport server refuses domain 0 and any
interface other than `lo`.

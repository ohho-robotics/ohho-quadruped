<!-- markdownlint-disable MD013 -->

# Train and export: Go2 velocity-tracking policy (scaffold)

**Status:** Scaffold only — not a finished RTX train. Sim-only; no hardware claims.

Linear: [OHH-122](https://linear.app/ohho-robotics/issue/OHH-122). Stack choice:
[ADR 0002](adr/0002-velocity-policy-training-stack.md).

## Goal

Velocity-tracking locomotion for the future sport shim: command ranges (train
envelope, wider than SafetyGate deploy caps):

| Axis | Train range (m/s or rad/s) | SafetyGate default (deploy) |
|---|---|---|
| `vx` | ±0.8 | 0.5 forward |
| `vy` | ±0.4 | 0.3 lateral |
| `wz` | ±1.0 | 1.0 yaw |

Terrains in scaffold configs: **flat** and **mild rough** (heightfield noise;
full terrain IDs are filled when rl_lab/mjlab envs are wired).

## Training stack (pick one)

1. **unitree_rl_lab** — default when Isaac Lab + RTX GPU are available on
   Varun's machine (see OHH-114).
2. **mjlab** — MuJoCo-native alternative; same obs/action contract in this repo.
3. **Community checkpoint** — only with documented licence + provenance; use
   `scripts/policy/download_velocity_checkpoint.sh` placeholder and manifest
   fields below.

**GPU gate:** Do not run multi-hour training in CI or agent sessions. Use
`python -m unittest discover -s tests` for smoke/spec validation.

## Observation vector (48 dims, fixed order)

All values are **body frame** unless noted. Scales are applied before the policy
(multiplicative, as in typical rl_lab normalizers).

| Index | Name | Dim | Scale |
|---|---|---|---|
| 0–2 | `base_lin_vel` | 3 | 2.0 |
| 3–5 | `base_ang_vel` | 3 | 0.25 |
| 6–8 | `projected_gravity` | 3 | 1.0 |
| 9–11 | `cmd_vel` (`vx`, `vy`, `wz`) | 3 | 1.0 |
| 12–23 | `joint_pos_rel` | 12 | 1.0 |
| 24–35 | `joint_vel` | 12 | 0.05 |
| 36–47 | `last_action` | 12 | 1.0 |

### Joint order (12)

`FR_hip`, `FR_thigh`, `FR_calf`, `FL_hip`, `FL_thigh`, `FL_calf`, `RR_hip`,
`RR_thigh`, `RR_calf`, `RL_hip`, `RL_thigh`, `RL_calf`.

### Default standing joints (rad, offset zero)

Hip 0.0; thigh 0.8; calf -1.5 per leg (12 values; see JSON configs).

## Action vector (12 dims)

Target **joint position offsets** added to default pose, scaled by **0.25** before
adding to defaults. Same joint order as observations.

## Control timing

| Parameter | Value |
|---|---|
| Policy rate | **50 Hz** |
| Sim substep (typical) | 2 ms |
| Decimation | 4 (500 Hz inner loop → 50 Hz policy) |

## PD gains (sim2sim placeholder)

Documented for sport-shim / low-level bridge alignment (tune against
`unitree_mujoco`):

| Joint group | Kp | Kd |
|---|---|---|
| Hip | 20 | 0.5 |
| Thigh | 20 | 0.5 |
| Calf | 20 | 0.5 |

## Config stubs

| File | Terrain |
|---|---|
| [ohho_go2/policy/config/flat_velocity.json](../../ohho_go2/policy/config/flat_velocity.json) | flat |
| [ohho_go2/policy/config/mild_rough_velocity.json](../../ohho_go2/policy/config/mild_rough_velocity.json) | mild rough |

## Export path (stub)

```bash
python scripts/policy/export_dummy_policy.py --out-dir artifacts/velocity_policy
```

Produces:

* `manifest.json` — format, obs/action spec version, **licence**, **seed**,
  **reward_curve** placeholder fields
* `dummy_policy_weights.json` — tiny linear policy for CI
* `export_stub.onnx.txt` — human reminder to run `torch.onnx.export` after train

Load smoke (no GPU):

```bash
python -m unittest discover -s tests
```

## Checkpoint download (placeholder)

```bash
bash scripts/policy/download_velocity_checkpoint.sh
```

When a real or community checkpoint is used, `manifest.json` must include:

* `licence` — SPDX or URL to terms
* `seed` — integer used for training
* `reward_curve` — path or inline summary (e.g. final episodic reward vs step)

## Sport shim and sim2sim (planned)

1. **Train** in rl_lab or mjlab with the obs/action contract above.
2. **Export** ONNX (preferred) into `artifacts/velocity_policy/`.
3. **Sim2sim:** sport shim (OHH-123) loads ONNX at 50 Hz; maps `Move(vx,vy,wz)`
   into `cmd_vel` slots 9–11; sends low-level targets to `unitree_mujoco` on DDS
   domain 1, interface `lo`.
4. **Deploy caps:** SafetyGate in ohho-sdk clamps commands to ADR 0001 defaults
   regardless of train envelope.

## Human TODOs (Varun GPU time)

- [ ] Run full GPU training (rl_lab or mjlab) from config stubs; log seed and
  reward curve.
- [ ] Replace dummy export with real ONNX/TorchScript artifact.
- [ ] Sim2sim: 20 s episode with `vx=0.3`, `vy=0`, `wz=0`; write metrics JSON
  (tracking error, max tilt, falls).
- [ ] Record short sim clip for demo/docs (sim only).

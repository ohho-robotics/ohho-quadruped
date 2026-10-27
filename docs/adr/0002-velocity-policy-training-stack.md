<!-- markdownlint-disable MD013 -->

# 0002: Go2 velocity-policy training stack (scaffold)

**Status:** Accepted (scaffold only — no trained weights in repo)
**Date:** 14 Oct 2026
**Linear:** [OHH-122](https://linear.app/ohho-robotics/issue/OHH-122)

## Context

ADR 0001 reserves Isaac Lab (`unitree_rl_lab`) for training the sport-shim
locomotion policy when an NVIDIA RTX GPU is available. OHH-122 adds repository
scaffolding (configs, export path, CI smoke) without running multi-day GPU
training in agent or CI sessions.

Nothing in this ADR implies a finished policy or hardware validation. Sim-only.

## Decision

| Priority | Stack | When to use |
|---|---|---|
| 1 (primary) | [unitree_rl_lab](https://github.com/unitreerobotics/unitree_rl_lab) (Isaac Lab) | Varun has a local RTX GPU and can run overnight-ish train jobs |
| 2 (lighter) | [unitree_rl_mjlab](https://github.com/unitreerobotics/unitree_rl_mjlab) (`mjlab`) | No Isaac install, or faster iteration on MuJoCo-native envs |
| 3 (fallback) | Licence-checked community checkpoint | GPU unavailable; must record licence, seed, and reward curve in manifest |

**GPU gate:** Training scripts and Isaac/mjlab envs are **human-operated only**.
CI and agents validate specs, dummy export, and config — never launch GPU training.

**Export target:** ONNX preferred for sport-shim inference; TorchScript acceptable.
The repo ships a **dummy export** (JSON manifest + linear weights) for CI; real
exports replace `artifacts/velocity_policy/` after human train.

## Consequences

* `docs/train-velocity-policy.md` is the runbook (obs/action order, terrains,
  sim2sim notes).
* `ohho_go2/policy/` holds spec + stubs only until M2 sport shim loads a real
  checkpoint (OHH-123+).
* Human TODOs remain: full GPU train, 20 s `vx=0.3` tracking metrics JSON, demo
  clip in sim.

## Alternatives considered

* **Train inside unitree_mujoco only:** Rejected for v1; RL env tooling lives in
  rl_lab / mjlab, not in the DDS sim loop.
* **Ship pretrained weights in git:** Rejected; use download script + manifest
  with licence fields when using community checkpoints.

## References

* [train-velocity-policy.md](../train-velocity-policy.md)
* ADR [0001-unitree-go2.md](0001-unitree-go2.md)

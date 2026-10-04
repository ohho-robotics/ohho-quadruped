# AGENTS.md — Coding Agent Guidelines for ohho-quadruped

## What this repo is

**M0 scaffold. Nothing is built. No robot code exists yet.**

This repository contains:
- Skeleton layout for future Go2 implementation (`ohho_go2/`, `sim/`, `ros2_ws/`, `docs/`)
- Credibility check v2 (`scripts/check_credibility.py`) and CI workflows
- AGENTS.md (this file) documenting rules for coding agents

Implementation (sport shim, DDS, sim, ROS 2 bridge, hardware) starts in
**November 2026** per ADR 0001 (proposed, PR #3):
https://github.com/ohho-robotics/ohho-quadruped/pull/3

Do NOT write sport shim code, DDS code, sim launchers, or robot-control logic
until M1/M2 work begins in November. Placeholder modules and READMEs must say
"planned, not built".

## Layout

```
ohho_go2/          Python package: sport shim + sim helpers (planned, November 2026)
sim/               unitree_mujoco launch + scenes (planned, November 2026)
ros2_ws/src/ohho_go2_bridge/   ROS 2 bridge (planned, early 2027)
docs/              ADRs and runbooks (see PR #3 for ADR 0001)
scripts/           Credibility check v2 (check_credibility.py + check-credibility.sh)
tests/             stdlib unittest tests
.github/workflows/ CI: credibility.yml + python.yml
```

## How to run checks

Run from the repo root:

```bash
python -m unittest discover -s tests
```

```bash
ruff check .
```

```bash
bash scripts/check-credibility.sh
```

- Ruff and Python 3.12 are required locally. Install ruff: `pip install ruff`.
- `OHHO_CRED_OFFLINE=1` skips the network git ls-remote call (for unit tests
  only). CI must not set this variable.
- ROS 2, colcon, Gazebo, MuJoCo, WSL2 Unitree tooling, and any robot hardware
  are not available in agent sessions. Say so; do not pretend otherwise.

## DDS domain rules

- Default for sim: **domain 1, interface `lo`** (loopback).
  `ChannelFactoryInitialize(1, "lo")` — not a real NIC.
- **Domain 0 or any non-loopback interface** requires:
  1. `OHHO_ARM_HARDWARE=1` environment variable, AND
  2. An **interactive TTY confirmation** ("I am physically present, the area is
     clear, the remote is in my hand") from a human operator, logged with a
     timestamp.
- **Agents and CI can never provide an interactive TTY confirmation.** Any
  non-TTY session must fail closed. No agent session may arm hardware.

## Sport-mode allowlist and prohibitions

Only the following sport-mode commands are permitted:
`stand_up`, `stand_down`, `balance_stand`, `recovery_stand`, `stop_move`,
`move`, `euler` (clamped to ±0.3 rad), `sit`, `rise_sit`.

The following are **strictly forbidden** in any agent session — do not write,
call, or suggest code that uses them:
- Flips, jumps, pounce
- Dance, handstand
- `walk_upright`
- `free_*` (any free_ variant)
- `cross_step`

## Test rules

- Tests use **Python stdlib `unittest`** — no pytest, no third-party test
  frameworks. This matches ohho-sdk CI.
- Run tests with: `python -m unittest discover -s tests`
- Test files go in `tests/`. Use `OHHO_CRED_OFFLINE=1` in unit tests to skip
  the network call.

## Hardware rules

- **Never run hardware commands from an agent session.**
- **Never contact a robot** (real or simulated over a non-loopback interface)
  from an agent session.
- Nothing runs on hardware unless Varun is physically present with the remote.
- No agent session ever sends commands to a real robot.

## Safety rules (must match SafetyGate, OHH-117)

> **Note:** SafetyGate (`ohho/safety.py`) lives in ohho-sdk and is **not yet
> built** (OHH-117 is in Backlog). The rules below are what agents must follow
> now, and they document the planned SafetyGate behaviour that will be enforced
> in code when OHH-117 lands.

### SafetyGate overview (planned)

`SafetyGate(Transport)` will wrap the real transport.
`Robot.connect` will insert it automatically for every transport whose
`protocol != "simulated"`.

### Velocity and acceleration caps

- Go2 defaults: **0.5 m/s linear, 0.3 m/s lateral, 1.0 rad/s yaw**,
  acceleration limited.
- Hard ceiling: `max_lin 1.5`, `max_ang 2.0` (the spec).
- The ceiling is raisable only by an explicit config file, **never by an agent**.

### Watchdog

- No command for **300 ms** → send zero velocity (matches sim-serve's deadman).
- No state for **500 ms** → `StopMove` and latch.

### E-stop

- Latched. Calls `StopMove()` first.
- `Damp()` only if the robot is already lying down, or `--estop-damp` is set
  (damping while standing drops the robot).
- Released **only** by an explicit `release_stop()` from a human-facing client.
- Agents and policies are never allowed to call e-stop or release it.

### Allowlist

Only these commands are permitted through SafetyGate:
`stand_up`, `stand_down`, `balance_stand`, `recovery_stand`, `stop_move`,
`move`, `euler` (clamped to ±0.3 rad), `sit`, `rise_sit`.

Flips, jumps, pounce, dance, handstand, `walk_upright`, `free_*`, and
`cross_step` are **always refused**.

### Tilt and fall guard

If |roll| or |pitch| > **0.6 rad**, or `error_code != 0`, stop and latch.

### Hardware arming

Any non-loopback interface or domain 0 requires:
1. `OHHO_ARM_HARDWARE=1`, AND
2. An **interactive TTY confirmation** ("I am physically present, the area is
   clear, the remote is in my hand"), logged with a timestamp.

Agents and CI **cannot arm**. A non-TTY session fails closed.

### Audit log

Every refused or clamped command goes to `~/.ohho/safety/<date>.jsonl`.

### Summary

Nothing runs on hardware unless Varun is physically present with the remote.
No agent session ever sends commands to a real robot.

## Credibility check v2 rules (honest-copy rule)

The credibility check (`scripts/check_credibility.py`) enforces:

- LICENSE: Apache 2.0 text, correct version and copyright lines.
- README: must have a `## Status` section with a table using only
  `Built` / `In progress` / `Vision` as status values.
- Every **Built** row must contain an evidence link (a relative path that
  exists in the repo, or an https:// URL).
- Banned terms in README (anywhere): `Spot`, `MPC`, `WebRTC`, `OhhO-Quadruped`,
  `OpenVLA`, `ROSBridge`, `docker compose`, `vcs import`.
- `Unitree`, `MuJoCo`, `Isaac` are allowed in README **only inside the status
  table rows or inside a "Sim only, not hardware-tested" section**.
- Every non-empty line in fenced command blocks (` ```bash `, ` ```sh `, etc.)
  in README must appear verbatim in a `run:` step of a CI workflow file.
- Claims guard: README and `docs/**/*.md` are scanned for working-capability
  claim phrases (e.g. "works on hardware", "tested on hardware",
  "production-ready", "fully working"). A line is exempt only if it contains a
  negation or planning marker (e.g. "not", "planned", "vision", "gated").
- The clone URL resolves `refs/heads/main` via `git ls-remote` (network check;
  CI always runs this — do not set `OHHO_CRED_OFFLINE` in CI).

**AGENTS.md is NOT scanned by the claims guard** (it is not README.md and not
under docs/). The prohibited phrases may appear in this file in the context of
documenting the rules. If you move content into docs/, ensure the claims guard
passes (use negation markers where needed).

**When you update the README status table:**
- A row must not be marked **Built** unless the code or CI it references
  actually exists in this PR/commit.
- Evidence links must be valid relative paths or real https:// URLs.
- Run `bash scripts/check-credibility.sh` locally before pushing.

## Git rules

- **One commit per logical change.** Each commit message starts with the
  Linear issue ID (e.g. `OHH-113:`).
- **Branch per issue.** Branch name mirrors the issue (e.g.
  `ohh-113-quadruped-scaffold`).
- PR body must include `Linear: <issue-url>` as the first line.
- **Never push to main.** Never amend, rebase, reset, or force-push.
- Do not commit secrets, `.env` files, virtualenvs, build output, or
  `node_modules`.
- `gh` CLI is not installed; do not use it and do not open PRs from an agent
  session. The operator opens the PR from the agent's output.

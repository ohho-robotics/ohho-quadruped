# Sibling Follow-ups for Go2 Honesty (OHH-133)

**Status: Planned sibling repository updates.**

This document records the exact honest-copy updates required in sibling repositories
outside this worktree (`ohho-os` / `ohho-sdk` and `site`).
Nothing in this document claims hardware capability; all physical robot hardware implementation
remains **Vision until Go2 EDU is available** (OHH-135).

---

## 1. ohho-os (`ohho-robotics/ohho-sdk`)

### File: `docs/unitree.md` (planned, to be created)

Create `docs/unitree.md` in `ohho-sdk` to document the Go2 adapter with honest capability claims:

#### Required content and rules:
1. **Simulation-tested only, not hardware-tested**:
   - The Go2 adapter (`ohho.adapters.unitree.UnitreeDdsTransport`) over `unitree_sdk2py` and CycloneDDS has been smoke-tested in simulation only (`unitree_mujoco` on DDS domain 1, interface `lo`).
   - Explicitly state: **Nothing has been tested on physical robot hardware.**
2. **Hardware bring-up status**:
   - Hardware bring-up is **Vision until a physical Go2 EDU is available** and an operator is physically present (OHH-135).
3. **Hardware arming safety gate**:
   - Default for sim: domain 1, interface `lo`.
   - Domain 0 or any non-loopback NIC strictly requires:
     1. `OHHO_ARM_HARDWARE=1` environment variable.
     2. An interactive TTY confirmation from a human operator physically present with the remote control.
     3. Agents, CI, and non-TTY sessions fail closed and can never arm hardware.
4. **Sport-mode command allowlist**:
   - Allowed: `stand_up`, `stand_down`, `balance_stand`, `recovery_stand`, `stop_move`, `move`, `euler` (clamped to ±0.3 rad), `sit`, `rise_sit`.
   - Prohibited (must be refused): flips, jumps, pounce, dance, handstand, `walk_upright`, `free_*`, `cross_step`.
5. **Contract test status**:
   - Document that `tests/hil/test_hil.py` (`TestHilUnitreeGo2`) is a hardware-in-the-loop contract stub that is skipped unless `OHHO_HIL=1`, and has not been run against a physical Go2.

---

## 2. site (`ohho-robotics/site`)

### File: `docs/ohho-os/robots.md`

#### Required edits:

1. **Section `## Built-in robots` (lines ~27–33)**:
   - Clarify `unitree-go2` status:
     - Replace:
       ```markdown
       `unitree-go2` and other named robots are roadmap. They are not a tested port.
       ```
     - With:
       ```markdown
       `unitree-go2` is sim-tested only (in-process or MuJoCo sim, not hardware-tested). Real hardware bring-up is Vision until a Go2 EDU is available and an operator is present (OHH-135). Other named robots remain roadmap.
       ```

2. **Section `## Protocol adapters` (lines ~74–82)**:
   - In the adapters table:
     - Current:
       ```markdown
       | `unitree` | `dds://` | Unitree G1, Go2, H1, B2, A2 | Cyclone DDS | `[unitree]` |
       ```
     - Change to:
       ```markdown
       | `unitree` | `dds://` | Go2 EDU (sim only, not hardware-tested) | Cyclone DDS | `[unitree]` |
       ```
     - Rationale: G1, H1, B2, and A2 are out of scope / roadmap per ADR 0001; do not claim support for models that have no adapter code or sim tests.

3. **Product Copy Brand-Free Guidelines**:
   - Keep marketing / product copy free of unvalidated brand claims.
   - Do not claim multi-brand support or production readiness for quadrupeds until verified by code and CI.

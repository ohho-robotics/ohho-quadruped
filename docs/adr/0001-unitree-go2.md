<!-- markdownlint-disable MD013 -->

# 0001: Unitree ADR: Go2 EDU target, sport-mode first, MuJoCo-first sim, safety rules

**Status:** Proposed - awaiting Varun's sign-off
**Date:** 4 Oct 2026

## Context

OhhO is planning support for the Unitree Go2 quadruped robot. The project relies
on several key choices regarding the target hardware, control level, simulator,
repository boundaries, ROS 2 distribution, safety rules, and project scheduling.
Making these choices explicit and recording them here avoids costly reversals
later.

Nothing is built yet: this is a decision record, the repository remains a
concept repository, and no capability exists today.

## Decisions

### Robot

* **Decision:** Target Unitree Go2 EDU only.
* **Reason:** The Air and Pro models have no official SDK or DDS access and
  require unofficial firmware, which is out of scope. Other models (G1, B2, H1,
  A2) are out of scope until the Go2 hardware implementation is complete.
* **Consequence:** We rely entirely on the official `unitree_sdk2` and its
  DDS interface.

### Control Level

* **Decision:** Use high-level sport-mode API (`Move`, `StandUp`, `StandDown`,
  `StopMove`, `Damp`, `BalanceStand`, `RecoveryStand`, `Euler`).
* **Reason:** This provides a stable, officially supported abstraction for the
  intelligence layer. Low-level control requires disabling sport mode and
  dealing with high-frequency control loops.
* **Consequence:** Low-level `rt/lowcmd` (which needs
  `MotionSwitcher.ReleaseMode`) is deferred to a later, optional phase.

### Simulator

* **Decision:** Use `unitree_mujoco` (Python simulator, DDS domain 1, interface
  `lo`).
* **Reason:** It is the official MuJoCo-based simulator. However, it only
  speaks low-level messages.
* **Consequence:** OhhO must add a "sport shim"—an RL velocity policy behind
  the sport API—to translate our sport-mode commands into low-level simulation
  commands. Isaac Lab (`unitree_rl_lab`) will be used only for training this
  policy, and only if an NVIDIA RTX GPU is available.

### Code Location

* **Decision:** The SDK backend, safety gate, and intelligence layer will reside
  in `ohho-sdk`.
* **Reason:** `ohho-sdk` is the standard location for robot-agnostic
  intelligence and hardware adapters.
* **Consequence:** `ohho-quadruped` will contain the sim launchers, sport shim,
  ROS 2 bridge, description, and demos. The engines will never import Unitree
  code directly.

### ROS 2 Version

* **Decision:** Target ROS 2 Humble for the bridge, with Jazzy as best-effort.
* **Reason:** Unitree officially tests and supports Humble.
* **Consequence:** We get a stable, vendor-supported environment for the
  quadruped, even though OmniBot uses Jazzy.

## Safety Rules

Nothing runs on hardware unless Varun is physically present with the remote.
No agent session ever sends commands to a real robot.

The safety layer (SafetyGate) wraps every non-simulated transport automatically
and enforces the following:

* **Caps:** 0.5 m/s forward, 0.3 m/s lateral, 1.0 rad/s yaw, plus acceleration
  limits. These are hard ceilings raisable only by a config file, never by the
  agent.
* **Watchdogs:** If there is no command for 300 ms, the velocity is zeroed. If
  there is no state for 500 ms, `StopMove` is sent and the system latches.
* **Latched E-stop:** Sends `StopMove` first. `Damp` is only sent if the robot
  is already lying down (damping while standing drops the 15 kg robot). Release
  is human-only.
* **Allowlist:** Only `stand_up`, `stand_down`, `balance_stand`,
  `recovery_stand`, `stop_move`, `move`, `euler` (+/-0.3 rad), `sit`, and
  `rise_sit` are permitted.
* **Never-list:** Flips, jumps, pounce, dances, handstand, `walk_upright`,
  `free_*`, and `cross_step` are strictly forbidden.
* **Tilt Guard:** If absolute roll or pitch exceeds 0.6 rad, or a nonzero error
  code is received, the robot stops and latches.
* **Hardware Arming:** Any non-loopback interface or domain 0 requires
  `OHHO_ARM_HARDWARE=1` AND an interactive TTY confirmation that Varun is
  physically present, the area is clear, and the remote is in hand. Agents, CI,
  and non-TTY sessions fail closed. The sport shim and ROS bridge refuse domain
  0 the same way.
* **Audit Log:** Every clamp and refusal is logged to `~/.ohho/safety/*.jsonl`.

## Scheduling

* **Decision:** Setup only in October (M0: this ADR, dev environment, repo
  scaffold, site tag fix; docs and setup, no implementation PRs, per OHH-105).
  SDK/implementation work (M1 onward) starts in November, unless Varun says
  otherwise.

### Milestones

* **M0 Setup and decisions:** ADR signed; WSL2 env prints Go2 sim state on
  Varun's PC; quadruped repo scaffolded with credibility check v2 and AGENTS.md;
  /github tags fixed. (OHH-112, 113, 114, 115) - **October** (docs and setup
  only).
* **M1 SDK backend correct and safe:** (OHH-116..120) - **November weeks 1-3**.
* **M2 Go2 in MuJoCo over DDS + CI:** (OHH-121..124) - **November weeks 1-3**.
* **M3 Intelligence layer on Go2 in sim:** (OHH-125..130) - **Late November to
  mid-December**.
* **M4 ROS 2 bridge:** (OHH-131, 132) - **By early January**.
* **M5 Docs, site claims and demo:** (OHH-133, 134) - **By early January**.
* **M6 Hardware bring-up:** Gated on a Go2 EDU (OHH-135..138) - **Whenever a Go2
  EDU is available**.

## Consequences

* Development is blocked on acquiring an NVIDIA RTX GPU (for training the sim
  shim policy) or adopting a fallback solution.
* Development of real-world functionality is gated on the physical presence of
  the operator, meaning automated CI cannot test real hardware.
* We accept the overhead of maintaining the `ohho-sdk` / `ohho-quadruped` split,
  ensuring the intelligence layer remains robot-agnostic.

## Alternatives Considered

* **Air/Pro models with unofficial firmware:** Rejected because it relies on
  unsupported hacks and breaks warranty, whereas the EDU provides official DDS
  access.
* **Low-level-first control:** Rejected because the high-level sport-mode API
  provides a much faster and safer path to integrating the intelligence layer.
  Low-level control is an optional future phase.
* **Isaac-first simulator:** Rejected because `unitree_mujoco` provides a
  lighter Python-based environment. Isaac Lab is reserved strictly for training
  the locomotion policy.
* **Gazebo for Go2:** Rejected in favor of MuJoCo, which is standard for Unitree
  RL training and supported by `unitree_mujoco`.
* **Jazzy-first ROS 2 bridge:** Rejected because Unitree only officially tests
  and supports Humble.

## Open Questions

* What is the exact Go2 lidar DDS topic and point format on the current
  firmware? (OHH-126, OHH-136)
* Can the `unitree_sdk2py` RPC server classes host the sport shim directly?
  (OHH-123)
* Do `unitree_go` / `unitree_api` ROS msgs build cleanly on Jazzy? (OHH-131)
* What are the real sport-mode Move timeout and rate limits? (OHH-137)
* Does Varun's PC have a suitable GPU? If not, a fallback for the locomotion
  policy is needed (e.g., mjlab, rented GPU, or a licence-checked community
  checkpoint).
* What is the current Go2 EDU UK price and lead time? (OHH-114, OHH-135)

## References

* Linear Issue:
  [OHH-112: Unitree ADR](https://linear.app/ohho-robotics/issue/OHH-112/unitree-adr-go2-edu-target-sport-mode-first-mujoco-first-sim-safety)
* Plan Document:
  [Unitree Go2 support, intelligence layer first](https://linear.app/ohho-robotics/document/plan-unitree-go2-support-intelligence-layer-first-cd2f1237891c)
* Upstream Repositories: `unitree_sdk2`, `unitree_sdk2_python`, `unitree_mujoco`,
  `unitree_ros2`, `unitree_rl_lab`, `unitree_rl_mjlab`

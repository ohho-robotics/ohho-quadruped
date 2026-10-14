# Go2 sport-mode motion (OHH-137)

**Needs Varun: physically present with the remote; Go2 EDU access (OHH-135).**

This file is a procedure for Varun to run later, at a real TTY, with the remote in his hand. It is not a record of a run. No step below has been executed. An agent session and CI must not arm hardware, must not open a DDS session to a robot, and must not type the arming phrase.

Do not start a step until the previous step is marked PASS in [go2-sport-motion-evidence-template.md](go2-sport-motion-evidence-template.md). A gap marked blocked stays blocked until the follow-up issue lands. Do not invent a flag to get around it.

## Prerequisite

OHH-136 read-only bring-up is green: `ohho connect` to the Go2 over DDS with `--read-only`, state arriving, no sport client and no motion.

That bring-up runbook is not in this repository. `origin/main` of ohho-quadruped has no OHH-136 procedure, and the local `ohh-136-go2-bringup-runbook` worktree is still at `d37ad72` (the same commit as `origin/main`). Follow-up: OHH-136, before step 1.

Re-check, still read-only, from the ohho-os checkout that contains PR [#29](https://github.com/ohho-robotics/ohho-os/pull/29) (`ohh-120-cli-go2-backend`):

```bash
ohho connect unitree-go2 --transport "dds://${OHHO_GO2_IFACE}?domain=0" --read-only
```

`--read-only` is "DDS state subscribe only — no SportClient or motion commands" on that branch. Do not pass `--arm`. `OHHO_GO2_IFACE` is the NIC recorded in the OHH-136 bring-up. OHH-119 reads that variable and otherwise uses `eth0`. Domain 0 is the real robot. `dds://lo?domain=1` is the simulator default and is the wrong URI for every hardware step here.

## Where the commands come from

The flags below were read with `git show` / `git grep` on the local ohho-os clone (`C:\Users\varun\ohho\ohho-sdk`). Those branches were not checked out, edited, or pushed. They are open draft PRs and they are not one combined tree. A step names the PR that actually contains the flag.

| Issue | PR | Branch tip read | What this procedure uses |
|---|---|---|---|
| OHH-117 | (safety gate; local branch `ohh-117-safety-gate`) | `81dbdfeb` | Caps, watchdogs, latch, allowlist, arming phrase |
| OHH-119 | [#26](https://github.com/ohho-robotics/ohho-os/pull/26) | `000217de` | `ohho selftest --allow-stand` |
| OHH-120 | [#29](https://github.com/ohho-robotics/ohho-os/pull/29) | `490bd29f` | `ohho drive`, `ohho connect --read-only`, hardware DDS refuses motion without a successful `--arm` |
| OHH-127 | [#30](https://github.com/ohho-robotics/ohho-os/pull/30) | `90079c99` | `Robot.stand()`, `Robot.emergency_stop()`, `ohho agent` |
| OHH-130 | [#34](https://github.com/ohho-robotics/ohho-os/pull/34) | `910b598a` | `ohho sim-serve --backend robot` |

OHH-117's Go2 profile, from `ohho/safety.py` on `ohh-117-safety-gate` (same `max_vx=0.5` line is present on the four branches above):

| Rule | Value |
|---|---|
| `max_vx` / `max_vy` / `max_wz` | 0.5 m/s, 0.3 m/s, 1.0 rad/s |
| Acceleration | 1.0 / 0.6 / 2.0 per second. Slowing toward zero is not limited. |
| Hard ceiling | 1.5 m/s linear, 2.0 rad/s angular. A safety config file can raise it. This procedure does not pass `--safety-config`. |
| Command watchdog | No velocity command for 300 ms while moving: zero velocity. Not latched. |
| State watchdog | No fresh state for 500 ms while armed: `StopMove` and latch. Go2 requires roll and pitch on that state. |
| E-stop | `emergency_stop()` sends `StopMove` first. `Damp()` only if body height is under 0.15 m, or if `estop_damp` / `--estop-damp` is set. Unknown posture does not damp. |
| Release | `release_stop()` on hardware asks the TTY for the word `release`, then leaves the gate disarmed. Human only. |
| Allowlist | `stand_up`, `stand_down`, `balance_stand`, `recovery_stand`, `stop_move`, `move`, `euler` (each angle clamped to ±0.3 rad), `sit`, `rise_sit`. |
| Always refused | flip, jump, pounce, dance, handstand, upright, `cross_step`, anything starting with `free`. |
| Tilt / fault | absolute roll or pitch over 0.6 rad, or `error_code != 0`: stop and latch. |
| Arming | `OHHO_ARM_HARDWARE=1`, no CI environment, interactive TTY, and the typed phrase `I am physically present, the area is clear, the remote is in my hand`. |
| Audit | `~/.ohho/safety/<UTC date>.jsonl` (override with `OHHO_SAFETY_DIR`). |

`Robot.connect` wraps every transport whose protocol is not `simulated`. The gate starts disarmed. `sim://` is not wrapped.

## Gaps

These are missing pieces. They are not optional wording.

1. **OHH-136.** No bring-up runbook in this repo yet. Step 1 waits on a green read-only bring-up.
2. **OHH-119 stand cycle is one pair, and it skips SafetyGate.** `check_stand_lie_cycle` calls `sport_command("stand_up")` then `sport_command("stand_down")` once (`settle_s` default 2.0). There is no repeat flag. `run_selftest` builds the transport with `resolve_transport`, not `Robot.connect`. OHH-117's `docs/safety.md` says selftest is outside the gate. Five cycles means five process runs. A missing audit file does not mean the gate clamped anything.
3. **OHH-120 has no `ohho stand` and no `ohho estop`.** `Robot.stand()` exists on OHH-127. `ohho sim` on OHH-120 stands only on `sim://`, and its pattern is not this procedure. `Robot.emergency_stop()` is a method, not a subcommand.
4. **OHH-127 scripted brain will move the robot and will ignore "1 m" and "blue cone".** With no harness, `ScriptedBrain._run_quadruped` stands, drives `vx=0.1` for 0.2 s, drives `vx=0.1` and `w=0.2` for 0.2 s, stops, and lies down. `evals/go2_sim_goals.yaml` has no 1 m goal and no blue-cone goal. Goal id 2 is "Stand up, drive forward 0.3 m, then stop and lie down" and is `scripted_pass: false`. Follow-up: OHH-127.
5. **OHH-130 `sim-serve --backend robot` never calls `arm()` and has no `--arm` flag.** Hardware DDS stays disarmed, so browser velocity is refused. The branch also has no HTML client. `estop: false` calls `release_stop()`. Follow-up: OHH-130. Steps 4 and the sim-serve form of step 3 stay blocked.
6. **OHH-121 and OHH-123 are not on this branch.** The offline rehearsal uses `fake://`. See the last section.

## Abort, every step

Stop with the remote, then mark the step FAIL, if any of these happen:

- The remote is not in Varun's hand, or someone enters the cleared area.
- The shell is not an interactive TTY. Arming fails closed. Do not retry from an agent.
- Absolute roll or pitch goes over 0.6 rad, or `error_code` is not 0. The gate latches when it is actually on the path.
- The robot does not stop at the end of the command.
- Any allowlisted command is answered by a fall.

After a latch, motion stays off until Varun types `release` at the TTY. That call leaves the gate disarmed. Arm again before any later motion. Do not pass `--estop-damp` on a standing robot. Damping while standing drops it.

Record for every step: a video of the robot and a clock, the path of `~/.ohho/safety/<UTC date>.jsonl`, and the command's own stdout or JSON. Copy those paths into the evidence template. Leave the template's result cell FAIL or unfilled until the pass line below is true. Do not write "tested on a Go2 EDU (date)" until that step's video, logs, and measurements exist.

## Step 1 — stand / lie down, five times

Checkout: ohho-os PR [#26](https://github.com/ohho-robotics/ohho-os/pull/26).

Set `OHHO_GO2_IFACE` in that TTY, then run this five times. Change only the `--out` number (`1` through `5`). There is no `--cycles` flag.

```bash
ohho selftest --robot unitree-go2 --allow-stand --transport "dds://${OHHO_GO2_IFACE}?domain=0" --out selftest-stand-lie-1.json
```

Each process does one `stand_up`, waits 2 s, one `stand_down`, waits 2 s. Five processes are the five cycles. `--allow-stand` is what enables the check; without it the check is SKIP.

SafetyGate caps are the table above, and they are **not** on this code path. Follow-up OHH-119 / OHH-117. Velocity caps do not apply to stand and lie. The remote is the stop.

Abort if a report's `stand_lie_cycle` status is FAIL, if the robot does not return to lying, or if it slips or falls. Abort the rest of the day if any report shows `error_code` other than 0.

Record the five JSON files, the video, and whether `~/.ohho/safety/` gained lines. Expect the audit file to stay quiet on this path. That quiet file is the gap, not a pass of the gate.

Pass: five reports, each with `checks.stand_lie_cycle.status` of `PASS`, robot lying at the end, no fall. The gate itself is not part of this pass.

## Step 2 — 0.3 m/s forward 1 m, back 1 m, then yaw 0.5 rad/s

The robot is lying at the end of step 1. `ohho drive` does not stand. OHH-120 has no stand subcommand. Stand with OHH-127's method, from PR [#30](https://github.com/ohho-robotics/ohho-os/pull/30), in an interactive TTY:

```bash
export OHHO_ARM_HARDWARE=1
python
```

```python
from ohho import Robot
bot = Robot.connect("unitree-go2", "dds://IFACE?domain=0")
bot.arm()          # type the arming phrase when asked; False means stop
bot.stand()        # SafetyGate command("stand_up"); must return True
bot.disconnect()
```

Replace `IFACE` with the same value as `OHHO_GO2_IFACE`. Do not set `estop_damp=True`. If `arm()` or `stand()` is false, stop. If the robot is not standing after disconnect, stop. Do not switch to `ohho sim` (that binary forces `sim://`).

Then, from PR [#29](https://github.com/ohho-robotics/ohho-os/pull/29), three drives. The CLI has `--seconds`, not a distance. At 0.3 m/s, 1 m is 3.333... s. `--seconds 3.34` is 1.002 m. Yaw duration is not in the issue text; this procedure uses 2 s so the command is finite (about 1 rad at 0.5 rad/s) and so the default 3 s is not used by accident.

```bash
export OHHO_ARM_HARDWARE=1
ohho drive unitree-go2 --transport "dds://${OHHO_GO2_IFACE}?domain=0" --arm --vx 0.3 --vy 0.0 --w 0.0 --seconds 3.34
ohho drive unitree-go2 --transport "dds://${OHHO_GO2_IFACE}?domain=0" --arm --vx -0.3 --vy 0.0 --w 0.0 --seconds 3.34
ohho drive unitree-go2 --transport "dds://${OHHO_GO2_IFACE}?domain=0" --arm --vx 0.0 --vy 0.0 --w 0.5 --seconds 2
```

On this PR, hardware DDS without a successful `--arm` exits 2 and sends no motion. Each process loops `drive` every 0.1 s, then `stop()` (zero velocity). Do not pass `--safety-config`. Do not pass `--vx` above 0.3 for the straight legs. The 0.5 m/s cap stays in force: 0.3 is under it, so the audit should contain `arm` and should not contain a clamp that changes 0.3. Lateral cap 0.3 m/s and yaw cap 1.0 rad/s apply if a later command exceeds them. Command watchdog is 300 ms. Proving a 2.0 m/s request clamps to 0.5 is the offline rehearsal, not a hardware overspeed command.

Abort if the printed `final odom` shows no forward progress, if the robot is still translating after the process exits, if it leaves the cleared lane, or if the audit shows a clamp that raised the speed. Abort on tilt or a non-zero `error_code`.

Record video, the three stdout `final odom` lines, and the audit JSONL.

Pass: forward odom change is about 1 m, the reverse leg comes back to about the start, yaw ran at the commanded 0.5 rad/s (under the 1.0 cap), the robot is stopped and still standing, and the audit shows the gate was armed.

## Step 3 — e-stop drill, three types, three trials each

Target: measured stop time under 0.5 s. The command watchdog inside SafetyGate is 0.3 s. Measure feet-stop on the video (clock in frame). Also copy audit timestamps. Three trials of each type. Do the types in the order below. The remote-damp trials drop a standing robot; keep the fall zone clear, and do them last.

### 3a. OhhO e-stop

There is no `ohho estop` subcommand (gap, OHH-120). Use `Robot.emergency_stop()` on PR [#30](https://github.com/ohho-robotics/ohho-os/pull/30), same arming rules as step 2. Do not construct the robot with `estop_damp=True`.

```python
from ohho import Robot
import time
bot = Robot.connect("unitree-go2", "dds://IFACE?domain=0")
bot.arm()
bot.stand()
end = time.monotonic() + 2.0
while time.monotonic() < end:
    bot.drive(vx=0.3, vy=0.0, w=0.0)
    time.sleep(0.1)
bot.emergency_stop()   # t0 for the video is this call
```

While standing, the gate sends `StopMove` and does not call `Damp()`. Audit: `estop` with `reason` `operator`, and no `damp` line. Velocity after the call is zero and the latch stays set. A later `drive` in that process must not move the robot.

The sim-serve form (`estop: true` on `--backend robot`) calls the same `emergency_stop()`, but that server never arms. It is not a pass path until OHH-130 grows an arm. Do not send `estop: false` to clear the latch; that calls `release_stop()` and will prompt this TTY for `release`.

Repeat so there are three video stop times.

### 3b. Client kill, watchdog

Killing `ohho drive` kills the process that contains the watchdog, so that kill does not measure the 300 ms path. The process that must stay alive is `ohho sim-serve`. PR [#34](https://github.com/ohho-robotics/ohho-os/pull/34):

```bash
ohho sim-serve --backend robot --robot unitree-go2 --transport "dds://${OHHO_GO2_IFACE}?domain=0" --host 127.0.0.1 --port 8765
```

`--host` and `--port` exist. Default bind is `0.0.0.0:8765`; this procedure binds loopback. There is no `--arm` on `sim-serve`. `Robot.connect` inside the server leaves a hardware link disarmed, so a browser `velocity` is refused and the robot does not walk. Follow-up: OHH-130. Until that lands, mark 3b blocked. Do not count "velocity was already zero" as a stop-time pass.

When the follow-up arms the server from this same TTY, the browser client (also not in that PR; whoever owns the page is the follow-up) sends JSON with `deadman: true` and `velocity.linear.x` of 0.3. Closing that client, while `sim-serve` is still running, is the drill: sim-serve zeros velocity after 300 ms with no message, and SafetyGate's command watchdog zeros velocity after 300 ms with no command. State is still arriving, so the 500 ms state latch should stay quiet. Pass is a measured stop under 0.5 s, three times, from a robot that was actually moving.

### 3c. Remote damping

No CLI. While the robot is walking under 3a or a later armed teleop, Varun presses the damping control on the Unitree remote in his hand. This runbook does not name a button chord. That damp drops a standing robot. `--estop-damp` is a different switch and stays off.

Record three stop times. Pass: motion is zero in under 0.5 s, the robot is down in the cleared area, and nobody was in the fall zone. Software stand is not part of this trial.

## Step 4 — browser teleop with deadman, on the robot

Blocked on OHH-130 (no `--arm`, no HTML client in the branch). The server command, once arming exists, is the same `sim-serve` line as step 3b. The client JSON in that PR's `docs/sim-serve.md` is:

```json
{
  "velocity": {"linear": {"x": 0.3, "y": 0.0}, "angular": {"z": 0.0}},
  "deadman": true,
  "estop": false
}
```

`mode` values the server already maps are `stand` to `stand_up`, `lie_down` to `stand_down`, and `recover` to `recovery_stand`.

SafetyGate caps stay in force on whatever velocity the page sends: 0.5 m/s forward, 0.3 m/s lateral, 1.0 rad/s yaw. Releasing deadman, or 300 ms of silence, zeros velocity. Varun holds the remote the whole time.

Abort if the robot moves with deadman released, if a command over 0.5 m/s is applied unclamped, or if the server was never armed (treat as blocked, not as a pass).

Record video, the server log, and the audit JSONL.

Pass: deadman held, the robot walks under the caps, releasing deadman stops it in under 0.5 s, and the remote was in hand. Not passable on the tip read for PR #34.

## Step 5 — one agent goal, then the blue cone

Checkout: ohho-os PR [#30](https://github.com/ohho-robotics/ohho-os/pull/30). Varun's hand stays on the e-stop (OhhO latch or the remote) for both goals.

The harness brain needs `ANTHROPIC_API_KEY` and the `ohho-os[agent]` extra. If the log contains `scripted brain`, mark FAIL immediately and stop the robot. That fallback moves the robot on a canned 0.4 s pattern and does not follow the sentence.

```bash
export OHHO_ARM_HARDWARE=1
ohho agent unitree-go2 --transport "dds://${OHHO_GO2_IFACE}?domain=0" --arm "stand up and walk 1 m forward"
```

Caps: the planner's Go2 linear cap is 0.5 m/s (`GO2_AGENT_MAX_LIN_M_S`), and SafetyGate clamps again to 0.5 / 0.3 / 1.0. Travel limit in that file is 6 m. `stand` goes through `SafetyGate.command("stand_up")`.

Abort on the scripted-brain line, on a fall, on tilt, or if the robot keeps moving after the process exits.

Record the full agent log, video, odom, and the audit JSONL.

Pass: the log shows the harness brain, the robot stands, forward travel is about 1 m, then it stops, and Varun did not have to hit the e-stop. The eval file's 0.3 m goal is a different sentence; do not substitute it and call this step done.

Second goal, only if the first is PASS. Put a real blue cone in the cleared area, in front of the robot, before starting:

```bash
ohho agent unitree-go2 --transport "dds://${OHHO_GO2_IFACE}?domain=0" --arm "go to the blue cone"
```

OHH-127 has no cone goal and no cone detector in `evals/go2_sim_goals.yaml`. Expect this to miss until that follow-up. Pass only if the robot stops at that cone, without a fall, with the harness brain. Anything else is FAIL. Do not add a flag to force a pass.

## Offline rehearsal

MuJoCo (`ohh-121-go2-mujoco-sim`) and the sport shim (`ohh-123-sport-shim`) are not on this branch. `scripts/rehearse_sport_motion.py` runs steps 1–3 on an in-process `fake://` transport: five stand/lie cycles, 0.3 m/s for 1 m forward and back, yaw 0.5 rad/s, clamps a 2.0 m/s request to 0.5 (lateral 1.0 to 0.3, yaw 3.0 to 1.0), and checks that OhhO e-stop, the 300 ms command watchdog, and remote damp each leave velocity at zero. It refuses any other transport string, including `dds://`.

```bash
python scripts/rehearse_sport_motion.py
```

The matching test is `tests/test_rehearse_sport_motion.py`, collected by `python -m unittest discover -s tests`. This repository's CI does not run pytest.

A passing table is a check of that fake transport. It is not evidence for the template, and it is not a hardware result.

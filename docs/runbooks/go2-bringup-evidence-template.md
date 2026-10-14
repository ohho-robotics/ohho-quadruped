# Go2 bring-up evidence (OHH-136)

**Needs Varun: physically present, Go2 EDU access (OHH-135).**

Blank sheet for [go2-bringup.md](go2-bringup.md). Copy this file out of
the git tree and fill the copy after a human session. Do not commit
measured values. The file in git stays blank so the offline checker can
prove it.

`EMPTY` means not measured. `REDACTED` is the only value allowed in git
for the serial. Result cells stay `EMPTY` until that out-of-tree copy is
filled. A filled result is `PASS` or a short explanation of a mismatch.
This template has not been filled from a robot session.

## Session

| Field | Value |
|---|---|
| Date (UTC) | EMPTY |
| Operator | EMPTY |
| Firmware version | EMPTY |
| Serial | REDACTED |
| Laptop NIC name | EMPTY |
| Laptop IPv4 | EMPTY |
| Selftest JSON path | EMPTY |
| Terminal log path | EMPTY |
| SafetyGate audit log path | EMPTY |

## SafetyGate audit (zero motion)

The in-repo cells stay empty. On the out-of-tree copy, quote nothing that
includes a serial. `connect` for `unitree-go2` with no `arm` event is the
line to look for. Any `arm`, `reject`, `clamp`, `damp`, or `estop` event
is an explanation, not a pass: the gate records `damp` when it calls
`sport_command("damp")` even if a read-only adapter then drops the RPC.

| Check | What to look for | Measured | Result |
|---|---|---|---|
| connect event | `connect` for unitree-go2, hardware true | EMPTY | EMPTY |
| not armed | no `arm` event, `--arm` not passed | EMPTY | EMPTY |
| no motion audit | no `reject`, `clamp`, `damp`, or `estop` | EMPTY | EMPTY |
| no release | no `estop_release` | EMPTY | EMPTY |
| robot stayed down | lying down the whole time, no foot shift | EMPTY | EMPTY |

## Checks

Expected values are the sim and code baselines from the runbook, not
measurements. Measured and Result stay `EMPTY` in git.

| Check | Expected (sim or code, not a measurement) | Measured | Result |
|---|---|---|---|
| pre-flight battery | above 50% before the cable is attached | EMPTY | EMPTY |
| area | clear 4x4 m, remote in hand, robot lying down | EMPTY | EMPTY |
| remote damping rehearsal | L2 long-press + B click, cable unplugged | EMPTY | EMPTY |
| laptop address | 192.168.123.x/24, not 192.168.123.161 | EMPTY | EMPTY |
| CYCLONEDDS_URI NIC | same name as the dds:// NIC | EMPTY | EMPTY |
| read-only connect | `--read-only` present, no SportClient | EMPTY | EMPTY |
| sportmodestate rate | sim floor 50 Hz; PR #26 hardware threshold 18 Hz | EMPTY | EMPTY |
| lowstate rate | sim floor 100 Hz; PR #26 hardware threshold 80 Hz | EMPTY | EMPTY |
| sport fields | position, velocity, yaw_speed, imu_rpy, error_code, body_height, mode, gait_type, foot_force | EMPTY | EMPTY |
| lowstate fields | 12 motors q/dq, bms soc | EMPTY | EMPTY |
| lidar topic name | PR #29 does not subscribe; OHH-126 assumes rt/utlidar/cloud | EMPTY | EMPTY |
| Move timeout | code constant 1.0 s on PR #29; do not call Move (OHH-137) | EMPTY | EMPTY |
| selftest command | `ohho selftest` without `--allow-stand`; do not run until gap 1 is merged | EMPTY | EMPTY |
| stand_lie_cycle | SKIP when the command is eventually run | EMPTY | EMPTY |
| OHHO_HIL | read-only test only; current TestHilUnitreeGo2 calls send_velocity, so skip | EMPTY | EMPTY |

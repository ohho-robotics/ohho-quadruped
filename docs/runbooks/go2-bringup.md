# Go2 bring-up (OHH-136) — read-only, no motion

**Needs Varun: physically present, Go2 EDU access (OHH-135).**

This runbook was written in advance. It has not been executed. No agent
session, CI job, or headless shell may run it. Varun runs it later, on a
native Ubuntu laptop, standing next to the robot with the remote in hand.

The robot stays lying down for the whole procedure. The laptop may subscribe
to telemetry. It must not initialise a sport client, stand the robot, or
send a velocity.

Blank sheet for the session: [go2-bringup-evidence-template.md](go2-bringup-evidence-template.md).
Copy that file out of the git tree before filling it in. The copy in git
stays blank.

## PRs that must merge first

Checked read-only on 14 Oct 2026 against the local `ohho-os` clone
(`C:\Users\varun\ohho\ohho-sdk`, nothing there was edited). Both pull
requests were still open drafts. Neither branch contains the other
(merge-base `85db848`).

| Need | Where it actually is | Snapshot |
|---|---|---|
| `ohho connect unitree-go2 --transport 'dds://<nic>?domain=0' --read-only` | [ohho-os PR #29](https://github.com/ohho-robotics/ohho-os/pull/29), branch `ohh-120-cli-go2-backend` | `490bd29` |
| `ohho selftest --robot unitree-go2 --transport 'dds://<nic>?domain=0'` | [ohho-os PR #26](https://github.com/ohho-robotics/ohho-os/pull/26), branch `ohh-119-selftest-legged` | `000217d` |
| `--allow-stand` (never passed by this procedure) | same PR #26 | `000217d` |

`--read-only` is a real flag on PR #29 (`ohho/cli.py`, stored as
`read_only`, passed into `UnitreeDdsTransport`). In
`ohho/adapters/unitree.py` the sport client is constructed only inside
`if not self.read_only`. With the flag set, `SportClient` is not imported
and not initialised. `send_velocity` and `StopMove` return immediately
because `self._client` is `None`.

`--allow-stand` is a real flag on PR #26 (`ohho/cli.py`, dest
`allow_stand`). The Go2 profile's `stand_lie_cycle` check is `SKIP` with
reason `Stand/lie cycle skipped (pass --allow-stand to enable)` unless the
flag is passed. This procedure never passes it.

PR #29 does not have `--allow-stand` or the Go2 self-test profile. PR #26
does not have `--read-only`. `origin/main` of ohho-os has neither. Do not
invent a combined command line and run it against a checkout that is
missing either flag.

## Gaps

These are missing on the snapshots above. Do not paper over them on the
robot.

1. **Self-test is not read-only.** PR #26 `run_selftest` calls
   `resolve_transport(uri, spec)` with no `read_only` argument, and it
   builds the adapter directly, not through `Robot.connect`, so SafetyGate
   is not in the path (`docs/safety.md` on PR #29 says the same thing).
   The PR #26 adapter always constructs `SportClient` and calls `StopMove`
   on `disconnect`. Follow-up: after PR #26 and PR #29 are both on one
   branch, thread `read_only=True` from `run_selftest` into
   `resolve_transport` for `unitree-go2` unless `--allow-stand` is set, and
   add a unit test where a fake sport client records zero calls to `Init`,
   `Move`, `StopMove`, `StandUp`, `StandDown`, and `Damp`. Do not run the
   self-test command until that follow-up is merged.
2. **The Go2 HIL test is not read-only.** `tests/hil/test_hil.py`
   `TestHilUnitreeGo2.test_drive_and_read` on both PR #26 and PR #29
   constructs `UnitreeDdsTransport(spec, iface)` with no `read_only`, then
   calls `send_velocity`. `OHHO_HIL=1 python -m unittest discover -s tests/hil`
   also runs the OmniBot serial tests. Follow-up: add a test that
   constructs `UnitreeDdsTransport(spec, "<nic>?domain=0", read_only=True)`,
   reads telemetry, never calls `send_velocity` or `sport_command`, and
   stays skipped unless `OHHO_HIL=1`. Do not run `tests/hil` for this
   bring-up until that test exists on a merged tree.
3. **There is no `ohho estop` subcommand.** PR #29's CLI has `--estop-damp`,
   which only changes what a later e-stop does. It does not fire one.
   The library call is `Robot.emergency_stop()` (`docs/safety.md` on
   PR #29). Follow-up, only if a later session needs a software e-stop
   while a sport client exists: a CLI that calls `emergency_stop` and
   refuses `--estop-damp` unless the operator asks for it. This bring-up
   does not need that call on the robot, because `--read-only` has no
   sport client to stop with. The remote is the e-stop.

## STOP — whole procedure

Stop, hold the remote, and use damping (below) if any of these happen.
Then unplug the Ethernet cable. Do not pass `--arm`. Do not type the
arming phrase. Do not call `release_stop`. Do not continue to the next
step.

- The robot stands, sits up, shifts its feet, or changes joint tone in a
  way you did not just cause with the remote's damping button.
- Any command line gains `--allow-stand`, `--arm`, `--estop-damp`,
  `OHHO_ARM_HARDWARE=1`, or a transport other than
  `dds://<nic>?domain=0` for the hardware steps (the only `sim://` command
  in this runbook is the unplugged rehearsal in step 1).
- The shell is WSL2, a container, SSH without a TTY, or any session that
  is not you at the laptop keyboard.
- Battery is not clearly above 50% before the cable is attached.
- The area is not clear, the remote is not in your hand, or the remote is
  not paired.
- The audit log shows `arm`, `reject`, `clamp`, `damp`, or `estop`. See
  step 3 for why a `damp` line is a stop even in read-only mode.

`release_stop` is human-only and is not part of this procedure.

## 1. Pre-flight

Do this with the Ethernet cable **unplugged**.

- Go2 EDU only. Air and Pro are out of scope (ADR 0001).
- Battery above 50% on the Unitree Go app or the robot's own battery
  indicator. If you cannot read the battery without a DDS session, stop.
- A clear 4x4 m area. People, chairs, and cables stay outside that square.
  You stand outside it with a clear view.
- Robot lying down, belly on the floor, feet not tucked under it in a
  stand pose. It stays lying down until you have left.
- Remote in hand and paired. On the handheld remote, the link lights mean
  the pairing took. The Unitree Go app remote-control setting is where
  that pairing is turned on.
- E-stop rehearsal, remote half: the only buttons you press are **L2
  (long press) + B (click)**. On the Go2 handheld remote sheet that is
  Damping Mode (soft emergency stop). Press it once now, while the robot
  is lying down and the cable is unplugged, so the gesture is rehearsed.
  Do not press L2+A, START, SELECT, or either stick. L2+A changes posture.
  START unlocks walking.
- E-stop rehearsal, ohho half: still unplugged, and only if the installed
  `ohho` already contains PR #29. This uses the in-process simulator. It
  does not open DDS.

```python
from ohho import Robot

bot = Robot.connect("unitree-go2", "sim://")
bot.emergency_stop()
bot.disconnect()
```

If that import or robot id fails because PR #29 is not installed, record
the gap and keep the remote rehearsal. Do not point this snippet at
`dds://`.

There is no CLI e-stop to rehearse (gap 3). Do not pass `--estop-damp`.
Damping from software while the posture is unknown is how a standing
robot gets dropped, and this procedure never stands it.

Local environment check, still unplugged. `ohho doctor` on PR #29 prints
the CycloneDDS environment and does not call `ChannelFactoryInitialize`.

```bash
ohho doctor
```

**STOP** if the robot stood up during the remote rehearsal, the battery
is at or below 50%, the area is not clear, or you are not holding the
remote.

## 2. Network

Native Ubuntu on the laptop. Not WSL2. WSL2's virtual NIC does not put
the robot's subnet on a Linux interface you can bind DDS to; that
limitation is already written in [docs/dev-setup.md](../dev-setup.md).
Sim work stays in WSL2. This step does not.

**STOP** if `uname -r` contains `microsoft`, or if the wired NIC you
intend to use is not visible to this Ubuntu (it is a Windows adapter
behind WSL).

Use a direct Ethernet cable between the laptop and the Go2 EDU. Not
Wi-Fi. Unitree's quick start
(https://support.unitree.com/home/en/developer/Quick_start) puts the
robot's onboard computer at `192.168.123.161` and tells you to address
the laptop's adapter as `192.168.123.x/24`. Their recommended example is
`192.168.123.222/24`. `192.168.123.99/24` is the other published example
(unitree_ros2 README, also noted in
`ros2_ws/src/ohho_go2_bridge/README.md`). Pick one. Do not assign both.
**Never assign `192.168.123.161`** to the laptop.

Example, replacing `eth0` with the laptop NIC that the cable is in:

```bash
sudo ip addr flush dev eth0
sudo ip addr add 192.168.123.222/24 dev eth0
sudo ip link set eth0 up
ip -4 addr show eth0
ping -c 3 192.168.123.161
```

**STOP** if the address is not `192.168.123.222/24` (or the single
alternate you chose), if the NIC is down, or if ping gets no reply. Do
not start DDS to "see if it works anyway".

Pin CycloneDDS to that same NIC. Save the following as
`$HOME/go2-cyclonedds.xml`. `Domain Id="any"` leaves the domain number to
the API call (`domain=0` below). The pin is the interface name. This
matches the loopback file in `docs/dev-setup.md`, with `lo` replaced.

```xml
<?xml version="1.0" encoding="UTF-8" ?>
<CycloneDDS xmlns="https://cdds.io/config">
  <Domain Id="any">
    <General>
      <Interfaces>
        <NetworkInterface name="eth0" priority="default" multicast="default" />
      </Interfaces>
    </General>
  </Domain>
</CycloneDDS>
```

```bash
export CYCLONEDDS_URI=file://$HOME/go2-cyclonedds.xml
```

Replace `eth0` in the XML with the name from `ip -4 addr`. The compact
form Unitree's ROS 2 setup uses is the same pin in one line, again with
your NIC name:

```bash
export CYCLONEDDS_URI='<CycloneDDS><Domain><General><Interfaces><NetworkInterface name="eth0" priority="default" multicast="default" /></Interfaces></General></Domain></CycloneDDS>'
```

Use either the file or the one-line form, not two different NIC names.

PR #29 connects with `ChannelFactoryInitialize(domain_id, iface)`. The
sim notes in `docs/dev-setup.md` say that call generates a config bound
to the named interface. The `<nic>` in the `dds://` URI and the
`NetworkInterface name` in `CYCLONEDDS_URI` must be the same string.
**STOP** if they differ.

Do not export `OHHO_ARM_HARDWARE`. Do not set `OHHO_HIL` in this step.

## 3. Read-only connect

Still no `--arm`, no `--allow-stand`, no `--estop-damp`, no
`OHHO_ARM_HARDWARE`.

Replace `<nic>` with the NIC from step 2. This is the PR #29 command:

```bash
ohho connect unitree-go2 --transport 'dds://<nic>?domain=0' --read-only
```

What that flag does on PR #29, and only on PR #29: telemetry
subscriptions to `rt/sportmodestate` and `rt/lowstate`. No `SportClient`.
The process starts disarmed. Do not pass `--arm`. Domain 0 on a
non-loopback NIC is the robot, so the safety gate treats the link as
hardware, but arming is a separate step that this command does not take.

`Robot.connect` wraps the adapter in SafetyGate. While disarmed, the
command watchdog does not zero the robot (`tick` returns immediately when
not armed). `disconnect` still calls the inner `send_velocity` of zeros.
On the read-only adapter that call returns without an RPC because
`self._client` is `None`.

A tilt or a non-zero `error_code` latches the gate even when disarmed
(`|roll|` or `|pitch|` above 0.6 rad). The latch calls
`emergency_stop` and, if body height is under 0.15 m (the lying-down
threshold), it also calls `sport_command("damp")`. On a read-only
adapter both calls return without an RPC. The audit line `damp` is still
written, because the gate records the call after `sport_command` returns
normally. So:

- Proof of "no sport client" is the connect path you typed
  (`--read-only`) plus a robot that did not move and did not change tone.
- An audit event `damp`, `estop`, `arm`, `reject`, or `clamp` is **STOP**,
  not a pass. Unplug. Do not decide that the no-op "must have been fine"
  and keep going.

Write down what the command prints (status, odom, battery, a joint
sample, roll and pitch). Battery on that print is `LowState.bms_state.soc`
divided by 100. **STOP** if the printed battery is at or below 50%, if
roll or pitch is large, if `error_code` is present and non-zero, or if
the robot moves.

Ctrl-C or let the command finish, then disconnect. Do not call
`release_stop`. Copy `~/.ohho/safety/<UTC date>.jsonl` aside (or the
directory in `OHHO_SAFETY_DIR` if you set one). You want the `connect`
event for `unitree-go2`. You do not want `arm`.

**STOP** if `ohho connect` does not accept `--read-only` (wrong install;
PR #29 is not what you are running). **STOP** if you feel the need to
add `--arm` to "get state". State is the part this command is for.

## 4. Self-test without --allow-stand

Do not pass `--allow-stand`.

The command the issue specifies, for after the gap is closed:

```bash
ohho selftest --robot unitree-go2 --transport 'dds://<nic>?domain=0'
```

Do not run the selftest command until gap 1 is merged. On the PR #26
snapshot this command initialises `SportClient` and sends `StopMove` on
disconnect, and it does not go through SafetyGate. `--out <path>` exists
on PR #26 and is the right way to choose the JSON path once the command
is actually safe to run. Do not pass `--allow-all-skip`. Do not pass
`--sim` and then treat the file as a robot result. `--sim` never talks
to the Go2.

When you are allowed to run it, the Go2 checks on PR #26 are `dds_link`,
`leg_motors`, `imu_rpy_rest`, `bms_soc`, `error_code`, `front_camera`,
and `stand_lie_cycle`. Without `--allow-stand`, `stand_lie_cycle` must
be `SKIP`. Any other status for that check is **STOP**. A `PASS` on
`stand_lie_cycle` means the robot was commanded to stand.

**STOP** if the shell suggests adding `--allow-stand`, if the robot
moves, or if the JSON shows a stand or lie command.

## 5. OHHO_HIL read-only

Do not run `tests/hil` on this bring-up.

`OHHO_HIL=1` is the existing opt-in for `tests/hil/test_hil.py`. The Go2
test behind that opt-in calls `send_velocity`. Discovering the whole
directory also targets OmniBot serial ports. Gap 2 is the follow-up that
adds a read-only test. Until that test is on the installed tree, this
step is a recorded skip, not a command you run.

**STOP** if a copied command includes `OHHO_HIL=1` together with
`unittest discover -s tests/hil`, `TestHilUnitreeGo2`, or `send_velocity`.

## 6. Compare with sim

Subscribe only. Do not publish `rt/lowcmd`, do not call `Move`, and do
not run `scripts/dev/smoke-unitree-sim.sh` against this NIC. That smoke
script publishes `rt/lowcmd` into the simulator.

Sim side, already recorded in this repo (domain 1, interface `lo`, no
robot):

| Item | Sim / code baseline | Where |
|---|---|---|
| Domain and NIC | domain 1, interface `lo` | `docs/dev-setup.md`, `scripts/dev/smoke-unitree-sim.sh` |
| State topics | `rt/sportmodestate` (`SportModeState_`), `rt/lowstate` (`LowState_`) | same smoke script; PR #29 subscribes to these two only |
| One sim sample | 973 messages on each topic in a 5 s smoke run on 4 Oct 2026 | `docs/dev-setup.md` verification log. That is one sim run, not a robot rate |
| Self-test rate floors | sim: sport ≥ 50 Hz, lowstate ≥ 100 Hz. Hardware thresholds in PR #26: sport ≥ 18 Hz, lowstate ≥ 80 Hz | `ohho/selftest.py` on PR #26. Thresholds, not measurements |
| Sport fields read | `position`, `velocity`, `yaw_speed`, `imu_rpy`, and if present `error_code`, `body_height`, `mode`, `gait_type`, `foot_force` | `sport_message_to_dict` on PR #29 |
| Low fields read | 12 motors `q` / `dq` in order FR, FL, RR, RL × hip, thigh, calf; `bms_state.soc / 100` as battery | `low_message_to_dict` on PR #29 |
| Move RPC timeout in code | `SportClient.SetTimeout(1.0)` (`_SPORT_RPC_TIMEOUT_SEC`) | PR #29. Not measured here. Real Move timeout is OHH-137 and requires a motion session this runbook does not start |
| Lidar | not subscribed by the PR #29 connect path. OHH-126 assumes `rt/utlidar/cloud` at 10 Hz, override `OHHO_LIDAR_DDS_TOPIC` | ADR 0001 open question (OHH-126, OHH-136) |

Fill the measured column on the evidence copy. Rates and field names that
do not match the baseline get a bug, not a quiet edit to the threshold.

### Bug report

File against ohho-os (adapter / self-test) or this repo (sim topic), and
link OHH-136.

```text
Title: OHH-136: <lidar topic name | Move timeout | rate | field mismatch>

Robot: Go2 EDU
Firmware: <from the evidence sheet>
Serial: REDACTED
Step: <3, 4, 5, or 6>
Expected (sim or the code snapshot above):
Measured:
Topic:
Motion commands sent: none
SafetyGate audit: <path, and whether arm/reject/clamp/damp/estop appeared>
PR snapshots: ohho-os #29 @ 490bd29, #26 @ 000217d
```

Do not attach a serial number, a video of a person, or a log that
contains either. Do not "confirm" a Move timeout by calling `Move`.

## Commands this procedure does not use

No flips, jumps, pounce, dance, handstand, `walk_upright`, `free_*`, or
`cross_step`. No `stand_up`, `stand_down`, `balance_stand`,
`recovery_stand`, `sit`, `rise_sit`, `move`, `euler`, `StopMove`, or
`Damp` from the laptop. Remote damping in step 1 is the only physical
command, and it is yours, on the remote, with the cable unplugged, while
the robot is already lying down.

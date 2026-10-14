#!/usr/bin/env python3
"""Offline rehearsal of OHH-137 sport-motion steps 1–3.

The MuJoCo launcher (branch ``ohh-121-go2-mujoco-sim``) and the sport shim
(branch ``ohh-123-sport-shim``) are not in this checkout, which tracks
``origin/main``. This module therefore drives an in-process fake transport.

It does not import DDS, open a socket, or contact a robot. The only accepted
transport name is ``fake://``. Caps below match SafetyGate's Go2 profile in
ohho-os OHH-117 (``max_vx`` 0.5 m/s, ``max_vy`` 0.3 m/s, ``max_wz`` 1.0 rad/s,
command watchdog 0.3 s). This file is not that gate and must not be pointed
at hardware.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field

MAX_VX_M_S = 0.5
MAX_VY_M_S = 0.3
MAX_WZ_RAD_S = 1.0
CMD_TIMEOUT_S = 0.3
WALK_VX_M_S = 0.3
YAW_W_RAD_S = 0.5
LEG_DISTANCE_M = 1.0
STAND_LIE_CYCLES = 5
COMMAND_PERIOD_S = 0.1
FAKE_TRANSPORT = "fake://"

# ``ohho drive`` has ``--seconds``, not a distance flag. 1 m at 0.3 m/s.
WALK_SECONDS = LEG_DISTANCE_M / WALK_VX_M_S


def _clamp(value: float, limit: float) -> float:
    if value > limit:
        return limit
    if value < -limit:
        return -limit
    return value


@dataclass
class FakeTransport:
    """In-memory sport commands. No I/O."""

    posture: str = "lying"
    vx: float = 0.0
    vy: float = 0.0
    w: float = 0.0
    x_m: float = 0.0
    yaw_rad: float = 0.0
    latched: bool = False
    silence_s: float = 0.0
    log: list[dict[str, object]] = field(default_factory=list)

    def command(self, action: str, *args: float) -> bool:
        if self.latched and action != "stop_move":
            self.vx = 0.0
            self.vy = 0.0
            self.w = 0.0
            self.log.append({"event": "reject", "action": action, "reason": "estop_latched"})
            return False
        if action == "stand_up":
            self.posture = "standing"
        elif action == "stand_down":
            self.posture = "lying"
        elif action == "stop_move":
            self.vx = 0.0
            self.vy = 0.0
            self.w = 0.0
        elif action == "move":
            requested = (float(args[0]), float(args[1]), float(args[2]))
            applied = (
                _clamp(requested[0], MAX_VX_M_S),
                _clamp(requested[1], MAX_VY_M_S),
                _clamp(requested[2], MAX_WZ_RAD_S),
            )
            self.vx, self.vy, self.w = applied
            self.silence_s = 0.0
            self.log.append(
                {
                    "event": "move",
                    "requested": requested,
                    "applied": applied,
                }
            )
            return True
        else:
            self.log.append({"event": "reject", "action": action, "reason": "not_in_rehearsal"})
            return False
        self.log.append({"event": action, "posture": self.posture})
        return True

    def advance(self, dt: float) -> None:
        """Integrate current velocity, then apply the command watchdog."""
        self.x_m += self.vx * dt
        self.yaw_rad += self.w * dt
        self.silence_s += dt
        moving = self.vx != 0.0 or self.vy != 0.0 or self.w != 0.0
        if self.silence_s + 1e-12 >= CMD_TIMEOUT_S and moving:
            self.vx = 0.0
            self.vy = 0.0
            self.w = 0.0
            self.log.append({"event": "watchdog_trip", "kind": "command"})

    def emergency_stop(self) -> None:
        """OhhO e-stop: StopMove, latch, damp only while lying."""
        self.command("stop_move")
        self.latched = True
        if self.posture == "lying":
            self.log.append({"event": "damp", "why": "lying_down"})
        else:
            self.log.append({"event": "damp_skipped", "why": "standing"})
        self.log.append({"event": "estop", "reason": "operator"})

    def remote_damp(self) -> None:
        """Physical-remote damp path: commanded velocity becomes zero."""
        self.vx = 0.0
        self.vy = 0.0
        self.w = 0.0
        self.log.append({"event": "remote_damp"})

    def hold_move(self, vx: float, vy: float, w: float, duration_s: float) -> None:
        """Re-send move every COMMAND_PERIOD_S, as ``ohho drive`` does."""
        if COMMAND_PERIOD_S >= CMD_TIMEOUT_S:
            raise RuntimeError("command period must stay inside the watchdog")
        elapsed = 0.0
        while elapsed + 1e-12 < duration_s:
            step = min(COMMAND_PERIOD_S, duration_s - elapsed)
            self.command("move", vx, vy, w)
            self.advance(step)
            elapsed += step


def _row(step: str, check: str, ok: bool, detail: str) -> dict[str, str]:
    return {
        "step": step,
        "check": check,
        "result": "PASS" if ok else "FAIL",
        "detail": detail,
    }


def rehearse() -> list[dict[str, str]]:
    """Run steps 1–3 on a fresh fake transport and return table rows."""
    rows: list[dict[str, str]] = []

    robot = FakeTransport()
    for _ in range(STAND_LIE_CYCLES):
        robot.command("stand_up")
        robot.command("stand_down")
    stand_ups = sum(1 for item in robot.log if item.get("event") == "stand_up")
    stand_downs = sum(1 for item in robot.log if item.get("event") == "stand_down")
    rows.append(
        _row(
            "1",
            "stand_lie_x5",
            stand_ups == STAND_LIE_CYCLES
            and stand_downs == STAND_LIE_CYCLES
            and robot.posture == "lying"
            and robot.vx == 0.0,
            f"cycles={stand_ups} posture={robot.posture}",
        )
    )

    robot = FakeTransport()
    robot.command("stand_up")
    robot.hold_move(WALK_VX_M_S, 0.0, 0.0, WALK_SECONDS)
    forward_x = robot.x_m
    rows.append(
        _row(
            "2",
            "forward_1m",
            abs(forward_x - LEG_DISTANCE_M) < 1e-9 and robot.vx == WALK_VX_M_S,
            f"x_m={forward_x:.3f} vx={robot.vx:.3f}",
        )
    )
    robot.hold_move(-WALK_VX_M_S, 0.0, 0.0, WALK_SECONDS)
    rows.append(
        _row(
            "2",
            "back_1m",
            abs(robot.x_m) < 1e-9 and robot.vx == -WALK_VX_M_S,
            f"x_m={robot.x_m:.3f} vx={robot.vx:.3f}",
        )
    )
    robot.hold_move(0.0, 0.0, YAW_W_RAD_S, 2.0)
    rows.append(
        _row(
            "2",
            "yaw_0.5",
            robot.w == YAW_W_RAD_S and abs(robot.yaw_rad - 1.0) < 1e-9,
            f"w={robot.w:.3f} yaw_rad={robot.yaw_rad:.3f}",
        )
    )

    robot.command("move", 2.0, 0.0, 0.0)
    rows.append(
        _row(
            "2",
            "cap_vx",
            robot.vx == MAX_VX_M_S,
            f"requested=2.0 applied={robot.vx:.3f}",
        )
    )
    robot.command("move", 0.0, 1.0, 0.0)
    rows.append(
        _row(
            "2",
            "cap_vy",
            robot.vy == MAX_VY_M_S,
            f"requested=1.0 applied={robot.vy:.3f}",
        )
    )
    robot.command("move", 0.0, 0.0, 3.0)
    rows.append(
        _row(
            "2",
            "cap_wz",
            robot.w == MAX_WZ_RAD_S,
            f"requested=3.0 applied={robot.w:.3f}",
        )
    )

    moving = FakeTransport(posture="standing")
    moving.command("move", WALK_VX_M_S, 0.0, 0.0)
    moving.emergency_stop()
    damp_skipped = any(
        item.get("event") == "damp_skipped" and item.get("why") == "standing"
        for item in moving.log
    )
    refused = moving.command("move", WALK_VX_M_S, 0.0, 0.0) is False
    rows.append(
        _row(
            "3",
            "ohho_estop",
            moving.latched
            and moving.vx == 0.0
            and moving.vy == 0.0
            and moving.w == 0.0
            and damp_skipped
            and refused,
            "vx=0 latched=1 damp=skipped_while_standing",
        )
    )

    watched = FakeTransport(posture="standing")
    watched.command("move", WALK_VX_M_S, 0.0, 0.0)
    watched.advance(CMD_TIMEOUT_S)
    rows.append(
        _row(
            "3",
            "client_watchdog",
            (not watched.latched)
            and watched.vx == 0.0
            and watched.vy == 0.0
            and watched.w == 0.0
            and any(item.get("event") == "watchdog_trip" for item in watched.log),
            "vx=0 latched=0 kind=command",
        )
    )

    remote = FakeTransport(posture="standing")
    remote.command("move", WALK_VX_M_S, 0.0, 0.0)
    remote.remote_damp()
    rows.append(
        _row(
            "3",
            "remote_damp",
            remote.vx == 0.0 and remote.vy == 0.0 and remote.w == 0.0,
            "vx=0",
        )
    )
    return rows


def format_table(rows: list[dict[str, str]]) -> str:
    headers = ("step", "check", "result", "detail")
    widths = {key: len(key) for key in headers}
    for row in rows:
        for key in headers:
            widths[key] = max(widths[key], len(row[key]))
    lines = [
        "  ".join(key.ljust(widths[key]) for key in headers),
        "  ".join("-" * widths[key] for key in headers),
    ]
    for row in rows:
        lines.append("  ".join(row[key].ljust(widths[key]) for key in headers))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    transport = FAKE_TRANSPORT
    index = 0
    while index < len(args):
        token = args[index]
        if token == "--transport":
            if index + 1 >= len(args):
                print("rehearse: --transport needs a value", file=sys.stderr)
                return 2
            transport = args[index + 1]
            index += 2
            continue
        print(f"rehearse: unknown argument {token}", file=sys.stderr)
        return 2
    if transport != FAKE_TRANSPORT:
        print(
            f"rehearse: refusing transport {transport!r}; only {FAKE_TRANSPORT} is accepted",
            file=sys.stderr,
        )
        return 2

    rows = rehearse()
    print(format_table(rows))
    print(
        "transport: fake://. MuJoCo (ohh-121-go2-mujoco-sim) and the sport shim "
        "(ohh-123-sport-shim) are not on this branch."
    )
    if all(row["result"] == "PASS" for row in rows):
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

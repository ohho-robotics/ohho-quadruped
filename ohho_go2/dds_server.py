"""Headless Go2 sport server for the MuJoCo sim.

Hosts the Unitree ``sport`` RPC service and publishes ``rt/lowcmd`` from
:class:`SportShimEngine`. Domain 1 and interface ``lo`` only.

``unitree_mujoco`` already publishes ``rt/sportmodestate``. This process does
not, so the two writers do not fight over that topic.
"""

from __future__ import annotations

import argparse
import os
import sys
import threading
import time
from typing import Any

from ohho_go2.dds_guard import SimDdsRefusalError, assert_sim_dds_only
from ohho_go2.sport_api import SUPPORTED_SPORT_API_IDS
from ohho_go2.sport_shim import LOWCMD_TOPIC, MotorCommand, SportShimEngine

MOTOR_MODE = 1
_SDK_MISSING = (
    "unitree_sdk2py is not installed. Source the Unitree env "
    "(for example: . /opt/unitree/env.sh) before starting the sport server."
)


def apply_motor_commands(slots: Any, motors: list[MotorCommand]) -> None:
    """Write the first motor slots. Extra slots are left alone. No SDK."""
    for index, motor in enumerate(motors):
        slot = slots[index]
        slot.mode = MOTOR_MODE
        slot.q = float(motor.q)
        slot.dq = float(motor.dq)
        slot.kp = float(motor.kp)
        slot.kd = float(motor.kd)
        slot.tau = float(motor.tau)


def make_sport_handler(engine: SportShimEngine, api_id: int):
    """RPC handler. ``(code, data)`` is what ``unitree_sdk2py`` Server expects."""

    def handle(parameter: str) -> tuple[int, str]:
        code, message = engine.handle_api(api_id, parameter)
        return int(code), str(message)

    return handle


class SportDdsServer:
    """Sport RPC plus a lowcmd publisher. Refuses domain 0 and non-``lo``."""

    def __init__(
        self,
        domain: int = 1,
        interface: str = "lo",
        engine: SportShimEngine | None = None,
        hz: float = 200.0,
    ) -> None:
        assert_sim_dds_only(domain, interface)
        self.domain = domain
        self.interface = interface
        self.engine = engine or SportShimEngine()
        self.hz = hz
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        assert_sim_dds_only(self.domain, self.interface)
        try:
            from unitree_sdk2py.core.channel import (  # type: ignore
                ChannelFactoryInitialize,
                ChannelPublisher,
            )
            from unitree_sdk2py.go2.sport.sport_api import (  # type: ignore
                SPORT_API_VERSION,
                SPORT_SERVICE_NAME,
            )
            from unitree_sdk2py.idl.default import unitree_go_msg_dds__LowCmd_  # type: ignore
            from unitree_sdk2py.idl.unitree_go.msg.dds_ import LowCmd_  # type: ignore
            from unitree_sdk2py.rpc.server import Server  # type: ignore
            from unitree_sdk2py.utils.crc import CRC  # type: ignore
        except ImportError as exc:
            raise SystemExit(_SDK_MISSING) from exc

        ChannelFactoryInitialize(self.domain, self.interface)
        server = Server(SPORT_SERVICE_NAME)
        server._SetApiVersion(SPORT_API_VERSION)
        for api_id in sorted(SUPPORTED_SPORT_API_IDS):
            server._RegistHandler(api_id, make_sport_handler(self.engine, api_id), False)
        server.Start(False)

        publisher = ChannelPublisher(LOWCMD_TOPIC, LowCmd_)
        publisher.Init()
        command = unitree_go_msg_dds__LowCmd_()
        command.head[0] = 0xFE
        command.head[1] = 0xEF
        command.level_flag = 0xFF
        crc = CRC()
        period = 1.0 / self.hz

        def loop() -> None:
            while not self._stop.is_set():
                motors, _state = self.engine.tick(period)
                apply_motor_commands(command.motor_cmd, motors)
                try:
                    command.crc = crc.Crc(command)
                except Exception:
                    command.crc = 0
                publisher.Write(command)
                _trace_velocity(self.engine)
                self._stop.wait(period)

        self._thread = threading.Thread(target=loop, name="ohho-go2-lowcmd", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=1.0)
            self._thread = None


_trace_keys: dict[int, tuple[float, float, float]] = {}


def _trace_velocity(engine: SportShimEngine) -> None:
    """One stdout line when commanded velocity changes. Off unless OHHO_SIM_TRACE=1."""
    if os.environ.get("OHHO_SIM_TRACE") != "1":
        return
    key = (
        round(engine.move_vx, 4),
        round(engine.move_vy, 4),
        round(engine.move_vyaw, 4),
    )
    if _trace_keys.get(id(engine)) == key:
        return
    _trace_keys[id(engine)] = key
    print(
        "ohho-sport-trace "
        f"t={time.time():.6f} vx={engine.move_vx:.4f} "
        f"vy={engine.move_vy:.4f} wz={engine.move_vyaw:.4f}",
        flush=True,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Go2 sport server for MuJoCo (DDS domain 1, interface lo)."
    )
    parser.add_argument("--domain", type=int, default=1)
    parser.add_argument("--interface", default="lo")
    args = parser.parse_args(argv)
    try:
        assert_sim_dds_only(args.domain, args.interface)
    except SimDdsRefusalError as exc:
        print(exc, file=sys.stderr)
        return 2
    server = SportDdsServer(domain=args.domain, interface=args.interface)
    try:
        server.start()
    except SystemExit as exc:
        if isinstance(exc.code, str):
            print(exc.code, file=sys.stderr)
        return 1
    print(
        f"sport server on domain {args.domain} interface {args.interface}",
        flush=True,
    )
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        server.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

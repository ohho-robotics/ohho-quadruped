"""Sport transport abstraction; default mock for CI and Windows dev."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


class SportTransport(Protocol):
    """Subset of sport-mode API used by the bridge (no hardware in tests)."""

    def move(self, vx: float, vy: float, vyaw: float) -> None: ...

    def stop_move(self) -> None: ...

    def invoke_mode(self, sport_command: str) -> None: ...


@dataclass
class MockSportTransport:
    """Records commands for unit tests and smoke runs."""

    moves: list[tuple[float, float, float]] = field(default_factory=list)
    stop_count: int = 0
    modes: list[str] = field(default_factory=list)
    estop_latched: bool = False

    def move(self, vx: float, vy: float, vyaw: float) -> None:
        if self.estop_latched:
            return
        self.moves.append((vx, vy, vyaw))

    def stop_move(self) -> None:
        self.stop_count += 1

    def invoke_mode(self, sport_command: str) -> None:
        if self.estop_latched:
            return
        self.modes.append(sport_command)

    def latch_estop(self) -> None:
        self.estop_latched = True
        self.stop_move()


def resolve_sport_transport(
    transport: SportTransport | None,
    *,
    use_mock: bool,
) -> tuple[SportTransport, bool]:
    """Choose a transport for this sim-only scaffold.

    An injected transport is used unchanged. Otherwise the result is always
    MockSportTransport. The second value is True when ``use_mock`` is false:
    a real Unitree transport is not available, so the caller stays on the mock.
    """
    if transport is not None:
        return transport, False
    return MockSportTransport(), not use_mock

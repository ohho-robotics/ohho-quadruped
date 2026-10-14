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

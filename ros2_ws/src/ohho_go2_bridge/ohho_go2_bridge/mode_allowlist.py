"""Allowed /ohho/mode commands (sport-mode allowlist subset: stand / lie poses)."""

from __future__ import annotations

# Maps ROS mode strings to sport API names (allowlist only).
MODE_TO_SPORT: dict[str, str] = {
    "stand": "stand_up",
    "balance_stand": "balance_stand",
    "recovery_stand": "recovery_stand",
    "lie": "stand_down",
    "sit": "sit",
    "rise_sit": "rise_sit",
}

FORBIDDEN_MODES = frozenset(
    {
        "flip",
        "jump",
        "pounce",
        "dance",
        "handstand",
        "walk_upright",
        "cross_step",
    }
)


def normalize_mode(mode: str) -> str:
    return mode.strip().lower().replace("-", "_")


def resolve_mode(mode: str) -> str:
    """
    Return sport command name for a mode string.

    Raises ValueError when the mode is unknown or forbidden.
    """
    key = normalize_mode(mode)
    if key in FORBIDDEN_MODES or key.startswith("free_"):
        raise ValueError(f"Mode {mode!r} is not on the sport allowlist.")
    sport = MODE_TO_SPORT.get(key)
    if sport is None:
        allowed = ", ".join(sorted(MODE_TO_SPORT))
        raise ValueError(f"Unknown mode {mode!r}; allowed: {allowed}")
    return sport

"""Refuse ROS domain 0 unless hardware is armed with an interactive TTY confirmation."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable, Mapping
from datetime import datetime, timezone

HARDWARE_ARM_ENV = "OHHO_ARM_HARDWARE"
CONFIRM_PHRASE = (
    "I am physically present, the area is clear, the remote is in my hand"
)


class DomainRefusedError(RuntimeError):
    """Raised when the process may not use the configured ROS domain."""


def parse_ros_domain_id(env: Mapping[str, str] | None = None) -> int:
    """Return ROS_DOMAIN_ID from the environment (default 0)."""
    env = env if env is not None else os.environ
    raw = env.get("ROS_DOMAIN_ID", "0").strip()
    try:
        return int(raw, 10)
    except ValueError as exc:
        raise DomainRefusedError(f"Invalid ROS_DOMAIN_ID: {raw!r}") from exc


def require_safe_ros_domain(
    *,
    env: Mapping[str, str] | None = None,
    stdin_is_tty: bool | None = None,
    prompt: Callable[[str], str] | None = None,
    log_confirm: Callable[[str], None] | None = None,
) -> int:
    """
    Fail closed on ROS_DOMAIN_ID=0 unless OHHO_ARM_HARDWARE=1 and TTY confirm.

    Returns the parsed domain id when allowed.
    """
    domain = parse_ros_domain_id(env)
    if domain != 0:
        return domain

    env = env if env is not None else os.environ
    if env.get(HARDWARE_ARM_ENV) != "1":
        raise DomainRefusedError(
            "ROS_DOMAIN_ID=0 is the robot DDS domain; set ROS_DOMAIN_ID>=1 for sim, "
            f"or export {HARDWARE_ARM_ENV}=1 with an interactive TTY to arm hardware."
        )

    is_tty = stdin_is_tty if stdin_is_tty is not None else sys.stdin.isatty()
    if not is_tty:
        raise DomainRefusedError(
            "ROS_DOMAIN_ID=0 requires an interactive TTY confirmation; "
            "agents and CI must not arm hardware."
        )

    ask = prompt if prompt is not None else input
    reply = ask(f"Type exactly to arm hardware:\n{CONFIRM_PHRASE}\n> ").strip()
    if reply != CONFIRM_PHRASE:
        raise DomainRefusedError("Hardware arming confirmation phrase did not match.")

    stamp = datetime.now(timezone.utc).isoformat()
    line = f"{stamp} hardware_armed ros_domain_id=0"
    if log_confirm is not None:
        log_confirm(line)
    else:
        print(line, file=sys.stderr)

    return domain

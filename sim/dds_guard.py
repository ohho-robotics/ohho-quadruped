"""Fail-closed checks for DDS domain / interface (sim vs hardware)."""

from __future__ import annotations

import sys
from datetime import datetime, timezone


def _sim_defaults(domain_id: int, interface: str) -> bool:
    return domain_id == 1 and interface == "lo"


def validate_dds_endpoint(domain_id: int, interface: str) -> None:
    """Allow domain 1 on loopback; anything else needs hardware arming + TTY."""
    if _sim_defaults(domain_id, interface):
        return

    import os

    if os.environ.get("OHHO_ARM_HARDWARE") != "1":
        raise SystemExit(
            "Refusing non-sim DDS endpoint "
            f"(domain={domain_id}, interface={interface!r}). "
            "Sim default is domain 1 on lo. "
            "Set OHHO_ARM_HARDWARE=1 only when physically present with the remote."
        )

    if not sys.stdin.isatty():
        raise SystemExit(
            "Refusing non-sim DDS endpoint without an interactive TTY confirmation."
        )

    prompt = (
        "I am physically present, the area is clear, the remote is in my hand"
    )
    print(prompt, flush=True)
    answer = input("Type the phrase above exactly to continue: ").strip()
    if answer != prompt:
        raise SystemExit("Hardware arming confirmation failed.")
    ts = datetime.now(timezone.utc).isoformat()
    print(f"[ohho] hardware armed at {ts} domain={domain_id} interface={interface}")

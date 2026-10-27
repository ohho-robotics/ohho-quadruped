#!/usr/bin/env python3
"""Offline check for the Go2 bring-up runbook and blank evidence template.

Reads three markdown files and exits 0 when the required sections and the
read-only / no ``--allow-stand`` rules are present. Does not import a DDS
library, open a socket, or contact a robot.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

RUNBOOK_REL = Path("docs/runbooks/go2-bringup.md")
TEMPLATE_REL = Path("docs/runbooks/go2-bringup-evidence-template.md")
DOCS_INDEX_REL = Path("docs/README.md")

RUNBOOK_HEADINGS: tuple[str, ...] = (
    "## 1. Pre-flight",
    "## 2. Network",
    "## 3. Read-only connect",
    "## 4. Self-test without --allow-stand",
    "## 5. OHHO_HIL read-only",
    "## 6. Compare with sim",
    "## Gaps",
    "## STOP — whole procedure",
)

RUNBOOK_PHRASES: tuple[str, ...] = (
    "--read-only",
    "ohho connect unitree-go2",
    "ohho selftest --robot unitree-go2 --transport",
    "Do not pass `--allow-stand`",
    "Do not pass `--arm`",
    "Do not run the selftest command until",
    "Do not run `tests/hil`",
    "OHHO_HIL=1",
    "send_velocity",
    "192.168.123",
    "CYCLONEDDS_URI",
    "4x4",
    "lying down",
    "L2",
    "PR #29",
    "PR #26",
    "https://github.com/ohho-robotics/ohho-os/pull/29",
    "https://github.com/ohho-robotics/ohho-os/pull/26",
    "SportClient",
    "rt/sportmodestate",
    "rt/lowstate",
    "rt/utlidar/cloud",
    "read_only=True",
    "Needs Varun: physically present, Go2 EDU access (OHH-135)",
)

# Shell fences are the copy-paste surface. These must never appear there.
FORBIDDEN_FENCE_TOKENS: tuple[str, ...] = (
    "--allow-stand",
    "--arm",
    "--estop-damp",
    "OHHO_ARM_HARDWARE",
    "OHHO_HIL",
    "send_velocity",
    "StandUp",
    "StopMove",
    "tests/hil",
    "release_stop",
)

FENCE_LANGS = {"bash", "sh", "shell", "console", "powershell"}

TEMPLATE_PHRASES: tuple[str, ...] = (
    "Date (UTC)",
    "Firmware version",
    "Serial",
    "REDACTED",
    "Selftest JSON path",
    "Terminal log path",
    "SafetyGate audit log path",
    "PASS",
    "EMPTY",
    "--allow-stand",
    "send_velocity",
)

DOCS_INDEX_PHRASES: tuple[str, ...] = (
    "runbooks/go2-bringup.md",
    "Needs Varun: physically present, Go2 EDU access (OHH-135)",
)


def fail_reasons(reasons: list[str]) -> int:
    for reason in reasons:
        print(f"bringup runbook check failed: {reason}", file=sys.stderr)
    return 1


def fenced_shell_lines(text: str) -> list[str]:
    """Return non-empty lines from fenced shell blocks."""
    lines: list[str] = []
    in_block = False
    for line in text.splitlines():
        stripped = line.strip()
        if not in_block:
            match = re.match(r"^```(\w+)\s*$", stripped)
            if match and match.group(1).lower() in FENCE_LANGS:
                in_block = True
        elif stripped == "```":
            in_block = False
        elif stripped:
            lines.append(stripped)
    return lines


def _split_row(line: str) -> list[str]:
    parts = [cell.strip() for cell in line.strip().strip("|").split("|")]
    return parts


def markdown_tables(text: str) -> list[tuple[list[str], list[list[str]]]]:
    """Return (header cells, body rows) for each GitHub-style table."""
    tables: list[tuple[list[str], list[list[str]]]] = []
    raw = text.splitlines()
    i = 0
    while i < len(raw):
        line = raw[i].strip()
        if not line.startswith("|"):
            i += 1
            continue
        if i + 1 >= len(raw) or not re.match(r"^\|[-| :]+\|$", raw[i + 1].strip()):
            i += 1
            continue
        header = _split_row(line)
        body: list[list[str]] = []
        i += 2
        while i < len(raw) and raw[i].strip().startswith("|"):
            body.append(_split_row(raw[i]))
            i += 1
        tables.append((header, body))
    return tables


def check_runbook(text: str) -> list[str]:
    reasons: list[str] = []
    for heading in RUNBOOK_HEADINGS:
        if heading not in text:
            reasons.append(f"runbook missing heading: {heading}")
    for phrase in RUNBOOK_PHRASES:
        if phrase not in text:
            reasons.append(f"runbook missing required text: {phrase}")

    shell = fenced_shell_lines(text)
    for line in shell:
        for token in FORBIDDEN_FENCE_TOKENS:
            if token in line:
                reasons.append(f"shell fence contains {token!r}: {line}")

    connect = [
        line
        for line in shell
        if "ohho connect unitree-go2" in line and "--read-only" in line and "domain=0" in line
    ]
    if not connect:
        reasons.append(
            "runbook has no shell fence with "
            "`ohho connect unitree-go2`, `--read-only`, and `domain=0`"
        )

    selftest_lines = [line for line in text.splitlines() if "ohho selftest" in line]
    if not selftest_lines:
        reasons.append("runbook does not mention the ohho selftest command")
    for line in selftest_lines:
        if "--allow-stand" in line:
            reasons.append(f"selftest line passes --allow-stand: {line.strip()}")

    connect_lines = [line for line in text.splitlines() if "ohho connect" in line]
    for line in connect_lines:
        if "--read-only" not in line:
            reasons.append(f"connect line missing --read-only: {line.strip()}")
        if "--arm" in line or "--allow-stand" in line:
            reasons.append(f"connect line has a forbidden flag: {line.strip()}")
    return reasons


def check_template(text: str) -> list[str]:
    reasons: list[str] = []
    for phrase in TEMPLATE_PHRASES:
        if phrase not in text:
            reasons.append(f"evidence template missing required text: {phrase}")

    if fenced_shell_lines(text):
        reasons.append("evidence template must not contain a shell fence")

    tables = markdown_tables(text)
    if not tables:
        reasons.append("evidence template has no tables")
        return reasons

    serial_ok = False
    measured_rows = 0
    for header, body in tables:
        if "Value" in header and "Field" in header:
            value_i = header.index("Value")
            field_i = header.index("Field")
            for row in body:
                if len(row) <= max(value_i, field_i):
                    reasons.append(f"session row is short: {row}")
                    continue
                value = row[value_i]
                field = row[field_i]
                if value not in {"EMPTY", "REDACTED"}:
                    reasons.append(f"session value is not empty: {field}={value}")
                if field == "Serial":
                    serial_ok = value == "REDACTED"
                if field in {"Date (UTC)", "Firmware version"} and value != "EMPTY":
                    reasons.append(f"{field} must stay EMPTY in git")
        if "Measured" in header:
            measured_i = header.index("Measured")
            result_i = header.index("Result") if "Result" in header else None
            for row in body:
                if len(row) <= measured_i:
                    reasons.append(f"measured row is short: {row}")
                    continue
                measured_rows += 1
                if row[measured_i] != "EMPTY":
                    reasons.append(f"measured cell is not EMPTY: {row}")
                if result_i is not None and (
                    len(row) <= result_i or row[result_i] != "EMPTY"
                ):
                    reasons.append(f"result cell is not EMPTY: {row}")
    if not serial_ok:
        reasons.append("serial cell must be REDACTED")
    if measured_rows < 6:
        reasons.append(f"expected at least 6 measured rows, found {measured_rows}")
    return reasons


def check_docs_index(text: str) -> list[str]:
    reasons: list[str] = []
    for phrase in DOCS_INDEX_PHRASES:
        if phrase not in text:
            reasons.append(f"docs/README.md missing required text: {phrase}")
    return reasons


def check_tree(root: Path) -> list[str]:
    """Return failure reasons. An empty list means the tree passes."""
    reasons: list[str] = []
    files = {
        "runbook": root / RUNBOOK_REL,
        "template": root / TEMPLATE_REL,
        "docs index": root / DOCS_INDEX_REL,
    }
    texts: dict[str, str] = {}
    for label, path in files.items():
        if not path.is_file():
            reasons.append(f"missing {label}: {path}")
            continue
        texts[label] = path.read_text(encoding="utf-8")
    if "runbook" in texts:
        reasons.extend(check_runbook(texts["runbook"]))
    if "template" in texts:
        reasons.extend(check_template(texts["template"]))
    if "docs index" in texts:
        reasons.extend(check_docs_index(texts["docs index"]))
    return reasons


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    reasons = check_tree(root)
    if reasons:
        sys.exit(fail_reasons(reasons))
    print("bringup runbook check: ok")


if __name__ == "__main__":
    main()

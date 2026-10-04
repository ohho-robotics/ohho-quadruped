#!/usr/bin/env python3
"""
check_credibility.py — Credibility check v2 for ohho-quadruped.

Run via: bash scripts/check-credibility.sh
Or directly: python3 scripts/check_credibility.py

Exit 0 on success, exit 1 on any failure, with a clear reason printed.

Rules implemented:
  a) License checks (Apache 2.0 text, copyright, forbidden files).
  b) README status table (## Status section, Built/In progress/Vision only,
     every Built row has an evidence link).
  c) Banned terms in README (Spot, MPC, WebRTC, OhhO-Quadruped, OpenVLA,
     ROSBridge, docker compose, vcs import) — whole-word where sensible.
  d) Unitree/MuJoCo/Isaac allowed only in status table rows or in a section
     headed "Sim only, not hardware-tested".
  e) Every non-empty line in fenced command blocks in README must appear
     verbatim in a `run:` step of some .github/workflows/*.yml.
     Set OHHO_CRED_OFFLINE=1 to skip ONLY the network check (not for CI).
  f) Claims guard: scan README.md and docs/**/*.md for working-capability
     claim phrases; a line is exempt only if it also contains a negation/
     planning marker.  docs/ may mention Unitree/MuJoCo/Isaac freely.
  g) Clone URL resolves refs/heads/main via git ls-remote (network check).
"""

from __future__ import annotations

import glob
import os
import re
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# (rule c) Banned everywhere in README — whole-word match where noted.
# Keep these as a named constant.
BANNED_README_TERMS: list[tuple[str, bool]] = [
    # (pattern, whole_word)
    ("Spot", True),
    ("MPC", True),
    ("WebRTC", True),
    ("OhhO-Quadruped", False),  # hyphenated, no simple word boundary needed
    ("OpenVLA", True),
    ("ROSBridge", True),
    ("docker compose", False),
    ("vcs import", False),
]

# (rule d) Terms allowed only inside the status table or the hardware-tested section.
RESTRICTED_README_TERMS: list[str] = ["Unitree", "MuJoCo", "Isaac"]

# (rule f) Working-capability claim phrases — case-insensitive.
CLAIM_PHRASES: list[str] = [
    "works on hardware",
    "tested on hardware",
    "hardware-tested",
    "hardware tested",
    "production-ready",
    "production ready",
    "fully working",
    "fully functional",
    "works today",
    "walks on",
    "deployed on",
]

# Negation/planning markers that exempt a line from the claims guard.
CLAIM_NEGATION_MARKERS: list[str] = [
    "not",
    "no",
    "nothing",
    "isn't",
    "doesn't",
    "hasn't",
    "never",
    "planned",
    "proposed",
    "vision",
    "until",
    "gated",
]

# Status values allowed in the Status column of the ## Status table.
ALLOWED_STATUS_VALUES: set[str] = {"Built", "In progress", "Vision"}

# Fenced code block languages we inspect for commands.
FENCED_LANGS: set[str] = {"bash", "sh", "shell", "console", "powershell"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def fail(reason: str) -> None:
    print(f"credibility check failed: {reason}", file=sys.stderr)
    sys.exit(1)


def warn(msg: str) -> None:
    print(f"  [warn] {msg}", file=sys.stderr)


def _whole_word(pattern: str) -> str:
    return r"(?<![A-Za-z0-9_-])" + re.escape(pattern) + r"(?![A-Za-z0-9_-])"


def find_fenced_commands(text: str) -> list[str]:
    """Return non-empty lines from all fenced command blocks."""
    commands: list[str] = []
    in_block = False
    for line in text.splitlines():
        stripped = line.strip()
        if not in_block:
            m = re.match(r"^```(\w+)\s*$", stripped)
            if m and m.group(1).lower() in FENCED_LANGS:
                in_block = True
        else:
            if stripped == "```":
                in_block = False
            elif stripped:
                commands.append(stripped)
    return commands


def collect_ci_run_steps(workflows_glob: str) -> set[str]:
    """
    Parse .github/workflows/*.yml and collect all lines that appear in
    `run:` steps.  Handles both single-line and multi-line `run: |` blocks.
    No PyYAML dependency.
    """
    run_lines: set[str] = []
    for wf_path in glob.glob(workflows_glob):
        text = Path(wf_path).read_text(encoding="utf-8")
        lines = text.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            # Single-line run: <cmd>
            m = re.match(r"^\s*run:\s+(.+)$", line)
            if m and not stripped.endswith("|"):
                run_lines.append(m.group(1).strip())
                i += 1
                continue
            # Multi-line run: |
            if re.match(r"^\s*run:\s*\|\s*$", line):
                # Determine indent of block by looking at next non-empty line
                i += 1
                while i < len(lines):
                    block_line = lines[i]
                    if not block_line.strip():
                        i += 1
                        continue
                    # Determine block indent
                    block_indent = len(block_line) - len(block_line.lstrip())
                    # Consume block
                    while i < len(lines):
                        bl = lines[i]
                        if not bl.strip():
                            i += 1
                            continue
                        current_indent = len(bl) - len(bl.lstrip())
                        if current_indent < block_indent:
                            break
                        run_lines.append(bl.strip())
                        i += 1
                    break
                continue
            i += 1
    return set(run_lines)


def extract_status_table_rows(readme_text: str) -> list[str]:
    """
    Return all non-header, non-separator rows from the ## Status table.
    We find ## Status, then consume the table lines.
    """
    rows: list[str] = []
    in_status = False
    in_table = False
    for line in readme_text.splitlines():
        stripped = line.strip()
        if re.match(r"^##\s+Status\s*$", stripped):
            in_status = True
            continue
        if in_status:
            if re.match(r"^##", stripped) and not re.match(r"^##\s+Status", stripped):
                break  # next section
            if stripped.startswith("|"):
                in_table = True
                # Skip header and separator rows
                if re.match(r"^\|[-| :]+\|$", stripped):
                    continue  # separator
                # Check if it's a header row (contains "Status" column header typically)
                # We'll collect all pipe rows except pure separator
                rows.append(stripped)
            elif in_table and not stripped:
                break  # blank line ends table
    return rows


def extract_sim_section_lines(readme_text: str) -> list[str]:
    """Return lines that are inside a section headed 'Sim only, not hardware-tested'."""
    lines_out: list[str] = []
    in_section = False
    for line in readme_text.splitlines():
        stripped = line.strip()
        if re.match(r"^#+\s+.*[Ss]im only.*not hardware-tested", stripped):
            in_section = True
            continue
        if in_section:
            if re.match(r"^#+", stripped):
                break
            lines_out.append(line)
    return lines_out


def line_has_evidence_link(row: str) -> bool:
    """
    Return True if the table row contains a Markdown link (http(s)://) or a
    relative path link [text](some/path).
    We require the path form to resolve — that check is done by the caller.
    """
    # https:// or http:// link
    if re.search(r"https?://", row):
        return True
    # Relative path link [text](relative/path)
    if re.search(r"\[.+?\]\([^)]+\)", row):
        return True
    return False


def extract_relative_links(row: str) -> list[str]:
    """Return relative (non-http) link targets from a table row."""
    paths: list[str] = []
    for m in re.finditer(r"\[.+?\]\(([^)]+)\)", row):
        target = m.group(1)
        if not target.startswith("http"):
            paths.append(target)
    return paths


# ---------------------------------------------------------------------------
# Check functions
# ---------------------------------------------------------------------------


def check_license(root: Path) -> None:
    lic = root / "LICENSE"
    if not lic.exists():
        fail("LICENSE is missing")
    text = lic.read_text(encoding="utf-8")
    if "Apache License" not in text:
        fail("LICENSE is not Apache-2.0 (missing 'Apache License')")
    if "Version 2.0, January 2004" not in text:
        fail("LICENSE is not Apache-2.0 (missing version line)")
    if "Copyright 2026 OhhO Robotics" not in text:
        fail("LICENSE copyright line changed")


def check_forbidden_files(root: Path) -> None:
    if (root / "docker-compose.yml").exists():
        fail("docker-compose.yml must not exist")
    if (root / "ohho.repos").exists():
        fail("ohho.repos must not exist")


def check_readme_basics(root: Path) -> None:
    readme = root / "README.md"
    if not readme.exists():
        fail("README.md is missing")
    text = readme.read_text(encoding="utf-8")
    if "https://github.com/ohho-robotics/OmniBot" not in text:
        fail("README is missing the OmniBot link")

    commands = find_fenced_commands(text)
    if not commands:
        fail("README has no fenced command blocks")

    clone_cmd = "git clone https://github.com/ohho-robotics/ohho-quadruped.git"
    if clone_cmd not in commands:
        fail("README clone URL is wrong or not in a fenced bash/sh block")

    if "Apache License 2.0" not in text:
        fail("README license line does not match LICENSE")


def check_status_table(root: Path) -> None:
    """Rule b: README must have a ## Status section with a valid table."""
    readme = root / "README.md"
    text = readme.read_text(encoding="utf-8")

    if "## Status" not in text:
        fail("README is missing a '## Status' section")

    rows = extract_status_table_rows(text)
    if not rows:
        fail("README ## Status section has no table rows")

    # Remove header row (first row, which has column names)
    data_rows = [r for r in rows if not re.search(r"\bItem\b|\bStatus\b|\bEvidence\b", r)
                 or re.search(r"Built|In progress|Vision", r)]

    for row in data_rows:
        # Extract the Status cell — second pipe-delimited cell
        cells = [c.strip() for c in row.split("|") if c.strip()]
        if len(cells) < 2:
            continue
        # Find which cell contains a known status value
        status_value = None
        for cell in cells:
            cell_clean = cell.strip()
            if cell_clean in ALLOWED_STATUS_VALUES:
                status_value = cell_clean
                break
        if status_value is None:
            fail(
                f"README Status table row has invalid Status value "
                f"(must be Built, In progress, or Vision): {row}"
            )
        if status_value == "Built":
            if not line_has_evidence_link(row):
                fail(
                    f"README Status table: Built row has no evidence link: {row}"
                )
            # Check relative links resolve
            for rel_path in extract_relative_links(row):
                target = root / rel_path
                if not target.exists():
                    fail(
                        f"README Status table: Built row links to path that does not "
                        f"exist: {rel_path}"
                    )


def check_banned_readme_terms(root: Path) -> None:
    """Rule c: banned terms must not appear anywhere in README."""
    readme = root / "README.md"
    text = readme.read_text(encoding="utf-8")
    for phrase, whole_word in BANNED_README_TERMS:
        if whole_word:
            pattern = _whole_word(phrase)
        else:
            pattern = re.escape(phrase)
        if re.search(pattern, text):
            fail(f"README contains banned term: {phrase!r}")


def check_restricted_readme_terms(root: Path) -> None:
    """Rule d: Unitree/MuJoCo/Isaac allowed only in status table rows or sim section."""
    readme = root / "README.md"
    text = readme.read_text(encoding="utf-8")

    table_rows = extract_status_table_rows(text)
    table_text = "\n".join(table_rows)

    sim_section_lines = extract_sim_section_lines(text)
    sim_section_text = "\n".join(sim_section_lines)

    for term in RESTRICTED_README_TERMS:
        pattern = re.escape(term)
        for lineno, line in enumerate(text.splitlines(), 1):
            if re.search(pattern, line):
                # Is this line in the table?
                if re.search(pattern, table_text) and line.strip() in [
                    r.strip() for r in table_rows
                ]:
                    continue
                # Is this line in the sim section?
                if line in sim_section_lines:
                    continue
                # Check if the line is actually a table row (starts with |)
                if line.strip().startswith("|") and re.search(pattern, table_text):
                    continue
                # Check if it's inside the sim section
                if re.search(pattern, sim_section_text) and line in sim_section_lines:
                    continue
                fail(
                    f"README line {lineno}: {term!r} appears outside the status "
                    f"table or 'Sim only, not hardware-tested' section: {line.strip()!r}"
                )


def check_fenced_commands_in_ci(root: Path) -> None:
    """Rule e: every fenced command in README must appear in a CI run: step."""
    readme = root / "README.md"
    text = readme.read_text(encoding="utf-8")
    commands = find_fenced_commands(text)

    # Also check that docker compose / vcs import are still banned
    for cmd in commands:
        if "docker compose" in cmd:
            fail(f"README fenced command contains 'docker compose': {cmd!r}")
        if "vcs import" in cmd:
            fail(f"README fenced command contains 'vcs import': {cmd!r}")

    if not commands:
        return

    wf_glob = str(root / ".github" / "workflows" / "*.yml")
    ci_lines = collect_ci_run_steps(wf_glob)

    for cmd in commands:
        # The README command must appear verbatim as a substring of at least one CI run step.
        found = any(cmd in ci_step for ci_step in ci_lines)
        if not found:
            fail(
                f"README fenced command not found in any CI workflow run: step: {cmd!r}\n"
                f"  Add a CI step that runs this command verbatim."
            )


def check_claims(root: Path) -> None:
    """
    Rule f: scan README.md and docs/**/*.md for working-capability claim phrases.
    A line is exempt only if it also contains a negation/planning marker.
    docs/ may mention Unitree/MuJoCo/Isaac freely (only claims are checked there).
    """
    targets: list[Path] = [root / "README.md"]
    docs_dir = root / "docs"
    if docs_dir.is_dir():
        targets.extend(docs_dir.rglob("*.md"))

    for path in targets:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(root)
        for lineno, line in enumerate(text.splitlines(), 1):
            line_lower = line.lower()
            for phrase in CLAIM_PHRASES:
                if phrase.lower() in line_lower:
                    # Check for negation marker
                    has_negation = False
                    for marker in CLAIM_NEGATION_MARKERS:
                        if re.search(r"\\b" + re.escape(marker) + r"\\b", line, re.IGNORECASE):
                            has_negation = True
                            break
                    if not has_negation:
                        fail(
                            f"{rel}:{lineno}: working-capability claim phrase "
                            f"{phrase!r} without negation marker: {line.strip()!r}"
                        )


def check_clone_resolves(root: Path) -> None:
    """Rule g: clone URL resolves refs/heads/main (network check)."""
    if os.environ.get("OHHO_CRED_OFFLINE", "") == "1":
        print("  [skip] clone URL network check (OHHO_CRED_OFFLINE=1)")
        return
    url = "https://github.com/ohho-robotics/ohho-quadruped.git"
    print(f"clone URL resolves ({url}):")
    try:
        result = subprocess.run(
            ["git", "ls-remote", "--heads", url, "refs/heads/main"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        ref = result.stdout.strip()
        if not ref:
            fail(f"clone URL did not resolve refs/heads/main: {url}")
        print(f"  {ref}")
    except subprocess.TimeoutExpired:
        fail("git ls-remote timed out (30 s)")
    except FileNotFoundError:
        fail("git not found in PATH")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    root = Path(__file__).resolve().parent.parent

    print("Running credibility check v2...")

    check_license(root)
    print("  [ok] LICENSE")

    check_forbidden_files(root)
    print("  [ok] forbidden files absent")

    check_readme_basics(root)
    print("  [ok] README basics (OmniBot link, clone URL, license line)")

    check_status_table(root)
    print("  [ok] README ## Status table")

    check_banned_readme_terms(root)
    print("  [ok] README banned terms")

    check_restricted_readme_terms(root)
    print("  [ok] README restricted terms (Unitree/MuJoCo/Isaac placement)")

    check_fenced_commands_in_ci(root)
    print("  [ok] fenced commands in CI")

    check_claims(root)
    print("  [ok] claims guard (README + docs/)")

    check_clone_resolves(root)
    print("  [ok] clone URL resolves")

    print("credibility check: ok")


if __name__ == "__main__":
    main()

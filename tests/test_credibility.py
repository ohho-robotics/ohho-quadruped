"""
tests/test_credibility.py — stdlib unittest tests for check_credibility.py.

All tests use OHHO_CRED_OFFLINE=1 to skip the network git ls-remote call.
Tests build temporary directories with fixture README/LICENSE/workflow/docs files.
"""

from __future__ import annotations

import os
import sys
import textwrap
import unittest
from pathlib import Path

# Ensure scripts/ is importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
os.environ.setdefault("OHHO_CRED_OFFLINE", "1")

import check_credibility as cc  # noqa: E402, I001  (must come after sys.path manipulation)


# ---------------------------------------------------------------------------
# Helper — build a minimal fixture repo tree.
# ---------------------------------------------------------------------------

VALID_LICENSE = textwrap.dedent("""\
    Apache License
    Version 2.0, January 2004
    http://www.apache.org/licenses/

    Copyright 2026 OhhO Robotics
""")

VALID_WORKFLOW = textwrap.dedent("""\
    name: credibility
    on: [push]
    jobs:
      check:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v4
          - name: Clone
            run: git clone https://github.com/ohho-robotics/ohho-quadruped.git /tmp/clone
          - name: Lint
            run: ruff check .
          - name: Tests
            run: python -m unittest discover -s tests
          - name: Credibility
            run: bash scripts/check-credibility.sh
""")

VALID_README = textwrap.dedent("""\
    # OhhO Quadruped

    [![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

    The working robot is [OmniBot](https://github.com/ohho-robotics/OmniBot).

    ## Status

    | Item | Status | Evidence |
    |---|---|---|
    | Credibility check v2 | Built | [scripts/check_credibility.py](scripts/check_credibility.py) |
    | Vision item | Vision | planned |

    ## Sim only, not hardware-tested

    Nothing here has been tested on hardware.

    ## Clone

    ```bash
    git clone https://github.com/ohho-robotics/ohho-quadruped.git
    ```

    ## Checks

    ```bash
    python -m unittest discover -s tests
    ```

    ```bash
    ruff check .
    ```

    ```bash
    bash scripts/check-credibility.sh
    ```

    ## License

    [Apache License 2.0](LICENSE).
""")


def make_repo(tmp: Path, readme: str = VALID_README, license_text: str = VALID_LICENSE,
              workflow: str = VALID_WORKFLOW, extra_files: dict[str, str] | None = None) -> Path:
    """Create a minimal fixture repo tree and return its root."""
    # LICENSE
    (tmp / "LICENSE").write_text(license_text, encoding="utf-8")
    # README
    (tmp / "README.md").write_text(readme, encoding="utf-8")
    # Workflow
    wf_dir = tmp / ".github" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    (wf_dir / "credibility.yml").write_text(workflow, encoding="utf-8")
    # scripts/check_credibility.py (needed for relative link evidence)
    scripts_dir = tmp / "scripts"
    scripts_dir.mkdir(exist_ok=True)
    (scripts_dir / "check_credibility.py").write_text("# placeholder\n", encoding="utf-8")
    # github workflows python.yml (needed if evidence links to it)
    (wf_dir / "python.yml").write_text("# placeholder\n", encoding="utf-8")
    # AGENTS.md (needed if evidence links to it)
    (tmp / "AGENTS.md").write_text("# placeholder\n", encoding="utf-8")
    # Extra files
    if extra_files:
        for rel, content in extra_files.items():
            p = tmp / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
    return tmp


def run_check(fn, *args, **kwargs):
    """Run a check function; return None on success, SystemExit.code on failure."""
    try:
        fn(*args, **kwargs)
        return None
    except SystemExit as e:
        return e.code


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


class TestLicense(unittest.TestCase):
    def test_valid_license_passes(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            root = make_repo(Path(tmp))
            self.assertIsNone(run_check(cc.check_license, root))

    def test_missing_license_fails(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("x", encoding="utf-8")
            self.assertEqual(run_check(cc.check_license, root), 1)

    def test_wrong_copyright_fails(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            bad_lic = VALID_LICENSE.replace(
                "Copyright 2026 OhhO Robotics", "Copyright 2025 Evil Corp"
            )
            (root / "LICENSE").write_text(bad_lic, encoding="utf-8")
            self.assertEqual(run_check(cc.check_license, root), 1)


class TestForbiddenFiles(unittest.TestCase):
    def test_docker_compose_fails(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            root = make_repo(Path(tmp))
            (root / "docker-compose.yml").write_text("x", encoding="utf-8")
            self.assertEqual(run_check(cc.check_forbidden_files, root), 1)

    def test_ohho_repos_fails(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            root = make_repo(Path(tmp))
            (root / "ohho.repos").write_text("x", encoding="utf-8")
            self.assertEqual(run_check(cc.check_forbidden_files, root), 1)

    def test_no_forbidden_files_passes(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            root = make_repo(Path(tmp))
            self.assertIsNone(run_check(cc.check_forbidden_files, root))


class TestStatusTable(unittest.TestCase):
    def test_valid_baseline_passes(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            root = make_repo(Path(tmp))
            self.assertIsNone(run_check(cc.check_status_table, root))

    def test_no_status_section_fails(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            readme = VALID_README.replace("## Status", "## Progress")
            root = make_repo(Path(tmp), readme=readme)
            self.assertEqual(run_check(cc.check_status_table, root), 1)

    def test_built_row_without_evidence_fails(self):
        from tempfile import TemporaryDirectory

        _BUILT_ROW = (
            "| Credibility check v2 | Built |"
            " [scripts/check_credibility.py](scripts/check_credibility.py) |"
        )
        with TemporaryDirectory() as tmp:
            readme = VALID_README.replace(
                _BUILT_ROW,
                "| Credibility check v2 | Built | no link here |",
            )
            root = make_repo(Path(tmp), readme=readme)
            self.assertEqual(run_check(cc.check_status_table, root), 1)

    def test_built_row_missing_relative_path_fails(self):
        from tempfile import TemporaryDirectory

        _BUILT_ROW = (
            "| Credibility check v2 | Built |"
            " [scripts/check_credibility.py](scripts/check_credibility.py) |"
        )
        with TemporaryDirectory() as tmp:
            readme = VALID_README.replace(
                _BUILT_ROW,
                "| Credibility check v2 | Built | [nonexistent](does/not/exist.py) |",
            )
            root = make_repo(Path(tmp), readme=readme)
            self.assertEqual(run_check(cc.check_status_table, root), 1)

    def test_built_row_with_https_link_passes(self):
        from tempfile import TemporaryDirectory

        _BUILT_ROW = (
            "| Credibility check v2 | Built |"
            " [scripts/check_credibility.py](scripts/check_credibility.py) |"
        )
        _HTTPS_ROW = (
            "| Credibility check v2 | Built |"
            " https://github.com/ohho-robotics/ohho-quadruped"
            "/blob/main/scripts/check_credibility.py |"
        )
        with TemporaryDirectory() as tmp:
            readme = VALID_README.replace(_BUILT_ROW, _HTTPS_ROW)
            root = make_repo(Path(tmp), readme=readme)
            self.assertIsNone(run_check(cc.check_status_table, root))

    def test_invalid_status_value_fails(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            readme = VALID_README.replace(
                "| Vision item | Vision | planned |",
                "| Vision item | WIP | planned |",
            )
            root = make_repo(Path(tmp), readme=readme)
            self.assertEqual(run_check(cc.check_status_table, root), 1)


class TestBannedTerms(unittest.TestCase):
    def _check_banned(self, term: str) -> int | None:
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            readme = VALID_README + f"\nSomething about {term} here.\n"
            root = make_repo(Path(tmp), readme=readme)
            return run_check(cc.check_banned_readme_terms, root)

    def test_spot_fails(self):
        self.assertEqual(self._check_banned("Spot"), 1)

    def test_mpc_fails(self):
        self.assertEqual(self._check_banned("MPC"), 1)

    def test_webrtc_fails(self):
        self.assertEqual(self._check_banned("WebRTC"), 1)

    def test_ohho_quadruped_fails(self):
        self.assertEqual(self._check_banned("OhhO-Quadruped"), 1)

    def test_spotlight_passes(self):
        # "Spotlight" should NOT trip the "Spot" whole-word ban
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            readme = VALID_README + "\nSpotlight on the project.\n"
            root = make_repo(Path(tmp), readme=readme)
            self.assertIsNone(run_check(cc.check_banned_readme_terms, root))

    def test_clean_readme_passes(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            root = make_repo(Path(tmp))
            self.assertIsNone(run_check(cc.check_banned_readme_terms, root))


class TestRestrictedTerms(unittest.TestCase):
    def test_unitree_outside_table_fails(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            readme = VALID_README + "\nUnitree Go2 walking demo.\n"
            root = make_repo(Path(tmp), readme=readme)
            self.assertEqual(run_check(cc.check_restricted_readme_terms, root), 1)

    def test_unitree_inside_table_passes(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            # Add a Vision row with Unitree in the table
            readme = VALID_README.replace(
                "| Vision item | Vision | planned |",
                "| Unitree Go2 EDU sim | Vision | planned |",
            )
            root = make_repo(Path(tmp), readme=readme)
            self.assertIsNone(run_check(cc.check_restricted_readme_terms, root))

    def test_unitree_in_sim_section_passes(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            readme = VALID_README.replace(
                "Nothing here has been tested on hardware.",
                "Nothing here has been tested on hardware. Unitree Go2 planned for sim.",
            )
            root = make_repo(Path(tmp), readme=readme)
            self.assertIsNone(run_check(cc.check_restricted_readme_terms, root))


class TestFencedCommandsInCI(unittest.TestCase):
    def test_readme_command_not_in_ci_fails(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            readme = VALID_README + textwrap.dedent("""\

                ```bash
                some-mystery-command --flag
                ```
            """)
            root = make_repo(Path(tmp), readme=readme)
            self.assertEqual(run_check(cc.check_fenced_commands_in_ci, root), 1)

    def test_all_commands_in_ci_passes(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            root = make_repo(Path(tmp))
            self.assertIsNone(run_check(cc.check_fenced_commands_in_ci, root))

    def test_docker_compose_in_fenced_block_fails(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            readme = VALID_README + textwrap.dedent("""\

                ```bash
                docker compose up
                ```
            """)
            root = make_repo(Path(tmp), readme=readme)
            self.assertEqual(run_check(cc.check_fenced_commands_in_ci, root), 1)


class TestClaims(unittest.TestCase):
    def test_claim_phrase_in_readme_fails(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            readme = VALID_README + "\nThis robot works on hardware.\n"
            root = make_repo(Path(tmp), readme=readme)
            self.assertEqual(run_check(cc.check_claims, root), 1)

    def test_negated_claim_in_readme_passes(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            readme = VALID_README + "\nThis robot does not work on hardware yet.\n"
            root = make_repo(Path(tmp), readme=readme)
            self.assertIsNone(run_check(cc.check_claims, root))

    def test_claim_phrase_in_docs_fails(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            root = make_repo(Path(tmp), extra_files={
                "docs/runbook.md": "The robot is fully functional.\n"
            })
            self.assertEqual(run_check(cc.check_claims, root), 1)

    def test_negated_claim_in_docs_passes(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            root = make_repo(Path(tmp), extra_files={
                "docs/runbook.md": "The robot is not fully functional yet. Planned.\n"
            })
            self.assertIsNone(run_check(cc.check_claims, root))

    def test_unitree_in_docs_passes(self):
        """docs/ may mention Unitree freely — claims guard does not ban Unitree."""
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            root = make_repo(Path(tmp), extra_files={
                "docs/design.md": "# Design\n\nWe plan to use Unitree Go2 EDU (proposed).\n"
            })
            self.assertIsNone(run_check(cc.check_claims, root))

    def test_sim_only_not_hardware_tested_passes(self):
        """The canonical phrase must pass — it contains 'not'."""
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            root = make_repo(Path(tmp), extra_files={
                "docs/note.md": "Sim only, not hardware-tested.\n"
            })
            self.assertIsNone(run_check(cc.check_claims, root))

    def test_no_agent_sends_commands_passes(self):
        """'No agent session ever sends commands to a real robot' must pass."""
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            root = make_repo(Path(tmp), extra_files={
                "docs/safety.md": "No agent session ever sends commands to a real robot.\n"
            })
            self.assertIsNone(run_check(cc.check_claims, root))


class TestADRFromPR3ClaimsCheck(unittest.TestCase):
    """
    Verify the ADR from origin/ohh-112-unitree-adr passes the claims guard.
    We run the check on the ADR content using a temp dir fixture (outside repo).
    The ADR file is NOT committed to this branch.
    """

    ADR_CONTENT = """\
<!-- markdownlint-disable MD013 -->

# 0001: Unitree ADR: Go2 EDU target, sport-mode first, MuJoCo-first sim, safety rules

**Status:** Proposed - awaiting Varun's sign-off
**Date:** 4 Oct 2026

## Context

OhhO is planning support for the Unitree Go2 quadruped robot. The project relies
on several key choices regarding the target hardware, control level, simulator,
repository boundaries, ROS 2 distribution, safety rules, and project scheduling.
Making these choices explicit and recording them here avoids costly reversals
later.

Nothing is built yet: this is a decision record, the repository remains a
concept repository, and no capability exists today.

## Decisions

### Robot

* **Decision:** Target Unitree Go2 EDU only.
* **Reason:** The Air and Pro models have no official SDK or DDS access and
  require unofficial firmware, which is out of scope. Other models (G1, B2, H1,
  A2) are out of scope until the Go2 hardware implementation is complete.
* **Consequence:** We rely entirely on the official `unitree_sdk2` and its
  DDS interface.

### Control Level

* **Decision:** Use high-level sport-mode API (Move, StandUp, StandDown,
  StopMove, Damp, BalanceStand, RecoveryStand, Euler).
* **Reason:** This provides a stable, officially supported abstraction for the
  intelligence layer. Low-level control requires disabling sport mode and
  dealing with high-frequency control loops.
* **Consequence:** Low-level rt/lowcmd (which needs
  MotionSwitcher.ReleaseMode) is deferred to a later, optional phase.

### Simulator

* **Decision:** Use unitree_mujoco (Python simulator, DDS domain 1, interface lo).
* **Reason:** It is the official MuJoCo-based simulator. However, it only
  speaks low-level messages.
* **Consequence:** OhhO must add a sport shim - an RL velocity policy behind
  the sport API - to translate our sport-mode commands into low-level simulation
  commands. Isaac Lab (unitree_rl_lab) will be used only for training this
  policy, and only if an NVIDIA RTX GPU is available.

### Code Location

* **Decision:** The SDK backend, safety gate, and intelligence layer will reside
  in ohho-sdk.
* **Reason:** ohho-sdk is the standard location for robot-agnostic
  intelligence and hardware adapters.
* **Consequence:** ohho-quadruped will contain the sim launchers, sport shim,
  ROS 2 bridge, description, and demos. The engines will never import Unitree
  code directly.

### ROS 2 Version

* **Decision:** Target ROS 2 Humble for the bridge, with Jazzy as best-effort.
* **Reason:** Unitree officially tests and supports Humble.
* **Consequence:** We get a stable, vendor-supported environment for the
  quadruped, even though OmniBot uses Jazzy.

## Safety Rules

Nothing runs on hardware unless Varun is physically present with the remote.
No agent session ever sends commands to a real robot.

The safety layer (SafetyGate) wraps every non-simulated transport automatically
and enforces the following:

* **Caps:** 0.5 m/s forward, 0.3 m/s lateral, 1.0 rad/s yaw, plus acceleration
  limits. These are hard ceilings raisable only by a config file, never by the
  agent.
* **Watchdogs:** If there is no command for 300 ms, the velocity is zeroed. If
  there is no state for 500 ms, StopMove is sent and the system latches.
* **Latched E-stop:** Sends StopMove first. Damp is only sent if the robot
  is already lying down (damping while standing drops the 15 kg robot). Release
  is human-only.
* **Allowlist:** Only stand_up, stand_down, balance_stand,
  recovery_stand, stop_move, move, euler (+/-0.3 rad), sit, and
  rise_sit are permitted.
* **Never-list:** Flips, jumps, pounce, dances, handstand, walk_upright,
  free_*, and cross_step are strictly forbidden.
* **Tilt Guard:** If absolute roll or pitch exceeds 0.6 rad, or a nonzero error
  code is received, the robot stops and latches.
* **Hardware Arming:** Any non-loopback interface or domain 0 requires
  OHHO_ARM_HARDWARE=1 AND an interactive TTY confirmation that Varun is
  physically present, the area is clear, and the remote is in hand. Agents, CI,
  and non-TTY sessions fail closed. The sport shim and ROS bridge refuse domain
  0 the same way.
* **Audit Log:** Every clamp and refusal is logged to ~/.ohho/safety/*.jsonl.

## Scheduling

* **Decision:** Setup only in October (M0: this ADR, dev environment, repo
  scaffold, site tag fix; docs and setup, no implementation PRs, per OHH-105).
  SDK/implementation work (M1 onward) starts in November, unless Varun says
  otherwise.

## Consequences

* Development is blocked on acquiring an NVIDIA RTX GPU (for training the sim
  shim policy) or adopting a fallback solution.
* Development of real-world functionality is gated on the physical presence of
  the operator, meaning automated CI cannot test real hardware.
* We accept the overhead of maintaining the ohho-sdk / ohho-quadruped split,
  ensuring the intelligence layer remains robot-agnostic.

## Alternatives Considered

* **Air/Pro models with unofficial firmware:** Rejected because it relies on
  unsupported hacks and breaks warranty, whereas the EDU provides official DDS
  access.
* **Low-level-first control:** Rejected because the high-level sport-mode API
  provides a much faster and safer path to integrating the intelligence layer.
  Low-level control is an optional future phase.
* **Isaac-first simulator:** Rejected because unitree_mujoco provides a
  lighter Python-based environment. Isaac Lab is reserved strictly for training
  the locomotion policy.
* **Gazebo for Go2:** Rejected in favor of MuJoCo, which is standard for Unitree
  RL training and supported by unitree_mujoco.
* **Jazzy-first ROS 2 bridge:** Rejected because Unitree only officially tests
  and supports Humble.

## Open Questions

* What is the exact Go2 lidar DDS topic and point format on the current
  firmware? (OHH-126, OHH-136)
* Can the unitree_sdk2py RPC server classes host the sport shim directly?
  (OHH-123)
* Do unitree_go / unitree_api ROS msgs build cleanly on Jazzy? (OHH-131)
* What are the real sport-mode Move timeout and rate limits? (OHH-137)
* Does Varun's PC have a suitable GPU? If not, a fallback for the locomotion
  policy is needed (e.g., mjlab, rented GPU, or a licence-checked community
  checkpoint).
* What is the current Go2 EDU UK price and lead time? (OHH-114, OHH-135)

## References

* Linear Issue: OHH-112
* Plan Document: Unitree Go2 support, intelligence layer first
* Upstream Repositories: unitree_sdk2, unitree_sdk2_python, unitree_mujoco,
  unitree_ros2, unitree_rl_lab, unitree_rl_mjlab
"""

    def test_adr_from_pr3_passes_claims_guard(self):
        """
        The ADR from origin/ohh-112-unitree-adr:docs/adr/0001-unitree-go2.md
        must pass the claims guard when treated as a docs/ file.
        Note: we use a copy of the content here (not committed to this branch).
        """
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            root = make_repo(Path(tmp), extra_files={
                "docs/adr/0001-unitree-go2.md": self.ADR_CONTENT,
            })
            result = run_check(cc.check_claims, root)
            self.assertIsNone(result, "ADR from PR #3 should pass the claims guard")


if __name__ == "__main__":
    unittest.main()

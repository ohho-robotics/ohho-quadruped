"""Offline tests for the Go2 bring-up runbook checker.

Stdlib unittest, matching the rest of this repo. The checker is imported
and also executed as a script. Nothing here opens a socket or imports DDS.
"""

from __future__ import annotations

import ast
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "check_bringup_runbook.py"
sys.path.insert(0, str(ROOT / "scripts"))

import check_bringup_runbook as checker  # noqa: E402, I001


def _stage(dest: Path) -> None:
    for rel in (checker.RUNBOOK_REL, checker.TEMPLATE_REL, checker.DOCS_INDEX_REL):
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, target)


class BringupRunbookCheckTests(unittest.TestCase):
    def test_repo_tree_passes(self) -> None:
        self.assertEqual(checker.check_tree(ROOT), [])

    def test_script_exits_zero(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("bringup runbook check: ok", proc.stdout)

    def test_missing_read_only_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _stage(root)
            path = root / checker.RUNBOOK_REL
            text = path.read_text(encoding="utf-8").replace("--read-only", "--rw")
            path.write_text(text, encoding="utf-8")
            reasons = checker.check_tree(root)
        self.assertTrue(any("read-only" in reason or "read_only" in reason for reason in reasons))

    def test_allow_stand_in_shell_fence_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _stage(root)
            path = root / checker.RUNBOOK_REL
            text = path.read_text(encoding="utf-8")
            text += "\n```bash\nohho selftest --robot unitree-go2 --allow-stand\n```\n"
            path.write_text(text, encoding="utf-8")
            reasons = checker.check_tree(root)
        self.assertTrue(any("--allow-stand" in reason for reason in reasons))

    def test_filled_measurement_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _stage(root)
            path = root / checker.TEMPLATE_REL
            text = path.read_text(encoding="utf-8")
            text = text.replace(
                "| read-only connect | `--read-only` present, no SportClient | EMPTY | EMPTY |",
                "| read-only connect | `--read-only` present, no SportClient | 20 Hz | PASS |",
                1,
            )
            path.write_text(text, encoding="utf-8")
            reasons = checker.check_tree(root)
        self.assertTrue(any("not EMPTY" in reason for reason in reasons))

    def test_checker_source_does_not_import_dds_or_sockets(self) -> None:
        tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
        banned = {"socket", "cyclonedds", "unitree_sdk2py", "ohho"}
        found: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_name = alias.name.split(".", 1)[0]
                    if root_name in banned:
                        found.append(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                root_name = node.module.split(".", 1)[0]
                if root_name in banned:
                    found.append(node.module)
        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()

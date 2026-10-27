"""clone_pinned tolerates a dest that actions/cache already filled.

The sim-smoke job restores ``.unitree/cyclonedds/install`` before
``scripts/ci/install-unitree-gha.sh`` runs. ``git clone`` refuses that
non-empty parent. These tests drive the real function with a local repo.
"""

from __future__ import annotations

import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_SCRIPT = _REPO / "scripts" / "ci" / "install-unitree-gha.sh"
_BEGIN = "# BEGIN clone_pinned\n"
_END = "# END clone_pinned\n"


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    cmd = [
        "git",
        "-c",
        "user.name=ohho",
        "-c",
        "user.email=ohho@example.com",
        *args,
    ]
    return subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)


def _head(path: Path) -> str:
    out = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return out.stdout.strip()


def _load_clone_pinned() -> str:
    text = _SCRIPT.read_text(encoding="utf-8")
    start = text.index(_BEGIN) + len(_BEGIN)
    stop = text.index(_END, start)
    body = text[start:stop]
    if "clone_pinned()" not in body:
        raise AssertionError("clone_pinned body missing from install script")
    return body


def _make_remote(remote: Path) -> str:
    """Bare repo whose default branch is one commit past the returned pin."""
    work = remote.parent / "seed"
    work.mkdir()
    subprocess.run(
        ["git", "init", "-b", "main"],
        cwd=work,
        check=True,
        capture_output=True,
        text=True,
    )
    (work / "a.txt").write_text("a\n", encoding="utf-8")
    _git(work, "add", "a.txt")
    _git(work, "commit", "-m", "A")
    (work / "b.txt").write_text("b\n", encoding="utf-8")
    _git(work, "add", "b.txt")
    _git(work, "commit", "-m", "B")
    pin = _head(work)
    (work / "c.txt").write_text("c\n", encoding="utf-8")
    _git(work, "add", "c.txt")
    _git(work, "commit", "-m", "C")
    subprocess.run(
        ["git", "clone", "--bare", str(work), str(remote)],
        check=True,
        capture_output=True,
        text=True,
    )
    return pin


class TestClonePinned(unittest.TestCase):
    def setUp(self) -> None:
        if sys.platform == "win32":
            self.skipTest("clone_pinned is bash; run this test under WSL or Ubuntu")
        if shutil.which("bash") is None or shutil.which("git") is None:
            self.skipTest("bash and git are required")
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.ws = self.root / "ws"
        self.ws.mkdir()
        self.remote = self.root / "remote.git"
        self.pin = _make_remote(self.remote)

    def _run(self, dest: Path) -> subprocess.CompletedProcess[str]:
        script = self.root / "run-clone.sh"
        parts = [
            "#!/usr/bin/env bash\n",
            "set -euo pipefail\n",
            "export UNITREE_WS=" + shlex.quote(str(self.ws)) + "\n",
            _load_clone_pinned(),
            'clone_pinned "$1" "$2" "$3"\n',
        ]
        script.write_text("".join(parts), encoding="utf-8", newline="\n")
        return subprocess.run(
            ["bash", str(script), str(self.remote), str(dest), self.pin],
            capture_output=True,
            text=True,
        )

    def test_non_git_install_tree_is_kept_and_source_is_pinned(self) -> None:
        dest = self.ws / "cyclonedds"
        install = dest / "install"
        install.mkdir(parents=True)
        (install / ".ohho-built-pin").write_text("ok\n", encoding="utf-8")
        (dest / "junk.txt").write_text("junk\n", encoding="utf-8")
        result = self._run(dest)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(_head(dest), self.pin)
        self.assertEqual((install / ".ohho-built-pin").read_text(encoding="utf-8"), "ok\n")
        self.assertFalse((dest / "junk.txt").exists())
        self.assertTrue((dest / "b.txt").is_file())
        self.assertFalse((dest / "c.txt").exists())

    def test_pinned_checkout_is_reused_without_the_remote(self) -> None:
        dest = self.ws / "cyclonedds"
        first = self._run(dest)
        self.assertEqual(first.returncode, 0, first.stderr + first.stdout)
        sentinel = dest / "sentinel.txt"
        sentinel.write_text("keep\n", encoding="utf-8")
        shutil.rmtree(self.remote)
        second = self._run(dest)
        self.assertEqual(second.returncode, 0, second.stderr + second.stdout)
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep\n")
        self.assertEqual(_head(dest), self.pin)

    def test_wrong_commit_checkout_is_replaced(self) -> None:
        dest = self.ws / "unitree_mujoco"
        subprocess.run(
            ["git", "clone", "--quiet", str(self.remote), str(dest)],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(_head(dest), self.pin)
        (dest / "junk.txt").write_text("junk\n", encoding="utf-8")
        stamp = dest / "install" / "STAMP"
        stamp.parent.mkdir()
        stamp.write_text("old\n", encoding="utf-8")
        result = self._run(dest)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(_head(dest), self.pin)
        self.assertFalse((dest / "junk.txt").exists())
        self.assertFalse(stamp.exists())
        self.assertTrue((dest / "b.txt").is_file())
        self.assertFalse((dest / "c.txt").exists())

    def test_refuses_to_remove_a_dir_outside_unitree_ws(self) -> None:
        dest = self.root / "outside"
        dest.mkdir()
        keep = dest / "keep.txt"
        keep.write_text("safe\n", encoding="utf-8")
        result = self._run(dest)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(keep.read_text(encoding="utf-8"), "safe\n")
        self.assertFalse((dest / ".git").exists())
        self.assertIn("refusing to remove", result.stderr)


if __name__ == "__main__":
    unittest.main()

"""Fail if rclpy loggers are called with printf-style extra arguments."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_LOGGER_METHODS = frozenset({"debug", "info", "warn", "warning", "error", "fatal"})
_SKIP_DIRS = frozenset(
    {".git", ".venv", "venv", "build", "install", "log", "__pycache__", "node_modules"}
)


def _iter_python_files() -> list[Path]:
    files: list[Path] = []
    for path in _REPO_ROOT.rglob("*.py"):
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        files.append(path)
    return files


def _is_get_logger(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "get_logger"
    )


def printf_style_logger_errors(source: str, filename: str = "<src>") -> list[str]:
    """Return descriptions of rclpy log calls that are not a single f-string or literal."""
    tree = ast.parse(source, filename=filename)
    errors: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr not in _LOGGER_METHODS or not _is_get_logger(node.func.value):
            continue
        if len(node.args) != 1:
            errors.append(
                f"{filename}:{node.lineno}: {node.func.attr}() must take one message argument"
            )
            continue
        message = node.args[0]
        if isinstance(message, ast.BinOp) and isinstance(message.op, ast.Mod):
            errors.append(f"{filename}:{node.lineno}: use an f-string instead of % formatting")
    return errors


class TestRclpyLogStyle(unittest.TestCase):
    def test_repo_uses_single_message_logger_calls(self) -> None:
        failures: list[str] = []
        for path in _iter_python_files():
            source = path.read_text(encoding="utf-8")
            relative = path.relative_to(_REPO_ROOT).as_posix()
            failures.extend(printf_style_logger_errors(source, relative))
        self.assertEqual(failures, [])

    def test_detector_flags_extra_positional_arg(self) -> None:
        source = "def f(self, value):\n    self.get_logger().info('ready %s', value)\n"
        errors = printf_style_logger_errors(source)
        self.assertEqual(len(errors), 1)

    def test_detector_allows_fstring(self) -> None:
        source = "def f(self, value):\n    self.get_logger().info(f'ready {value}')\n"
        self.assertEqual(printf_style_logger_errors(source), [])

    def test_bridge_drops_placeholder_and_not_implemented(self) -> None:
        bridge = _REPO_ROOT / "ros2_ws" / "src" / "ohho_go2_bridge"
        text = "\n".join(
            path.read_text(encoding="utf-8") for path in sorted(bridge.rglob("*.py"))
        )
        self.assertNotIn("NotImplementedError", text)
        self.assertNotIn("publish_placeholder_sensor_topics", text)
        self.assertNotIn("publish_sim_sensors", text)


if __name__ == "__main__":
    unittest.main()

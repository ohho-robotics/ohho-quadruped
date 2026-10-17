#!/usr/bin/env python3
"""Launch Go2 in MuJoCo via pinned unitree_mujoco; OhhO scenes on DDS domain 1 / lo."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from sim.launcher import run_simulation  # noqa: E402
from sim.pins import SCENE_CHOICES  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="OhhO Go2 MuJoCo sim (unitree_mujoco simulate_python, pinned)."
    )
    parser.add_argument(
        "--scene",
        choices=SCENE_CHOICES,
        default="flat",
        help="OhhO MJCF scene (default: flat)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="No viewer; use offscreen GL (EGL/OSMesa via MUJOCO_GL)",
    )
    parser.add_argument(
        "--domain",
        type=int,
        default=1,
        help="CycloneDDS domain id (default: 1 for sim)",
    )
    parser.add_argument(
        "--iface",
        default="lo",
        help='DDS network interface (default: "lo")',
    )
    parser.add_argument(
        "--no-joystick",
        action="store_true",
        help="Disable pygame joystick / wireless controller emulation",
    )
    parser.add_argument(
        "--render-front-camera",
        action="store_true",
        help="Render the ohho_front_camera offscreen each step (headless / CI)",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=None,
        metavar="SECONDS",
        help="Stop after this many seconds (optional; default run until interrupt)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    run_simulation(
        scene=args.scene,
        headless=args.headless,
        domain_id=args.domain,
        interface=args.iface,
        use_joystick=not args.no_joystick,
        render_front_camera=args.render_front_camera,
        duration_s=args.duration,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

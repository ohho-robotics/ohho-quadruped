#!/usr/bin/env python3
"""Write dummy velocity-policy export bundle for CI / local smoke."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ohho_go2.policy.export_stub import write_export_bundle  # noqa: E402
from ohho_go2.policy.spec import config_dir, load_spec_from_config  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Export dummy Go2 velocity policy bundle.")
    parser.add_argument(
        "--config",
        type=Path,
        default=config_dir() / "flat_velocity.json",
        help="Velocity policy JSON config",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=REPO_ROOT / "artifacts" / "velocity_policy",
    )
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    spec = load_spec_from_config(args.config)
    paths = write_export_bundle(args.out_dir, spec, seed=args.seed)
    for name, path in paths.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

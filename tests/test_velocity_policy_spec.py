"""Validate velocity policy JSON configs against the frozen spec."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from ohho_go2.policy.spec import (  # noqa: E402
    ACTION_DIM,
    OBS_DIM,
    config_dir,
    load_spec_from_config,
)


class TestVelocityPolicySpec(unittest.TestCase):
    def test_flat_config_matches_contract(self) -> None:
        spec = load_spec_from_config(config_dir() / "flat_velocity.json")
        self.assertEqual(spec.obs_dim, OBS_DIM)
        self.assertEqual(spec.action_dim, ACTION_DIM)
        self.assertEqual(spec.cmd_vel_limits["vx"], 0.8)
        self.assertEqual(spec.cmd_vel_limits["vy"], 0.4)
        self.assertEqual(spec.cmd_vel_limits["wz"], 1.0)
        self.assertEqual(spec.policy_hz, 50.0)

    def test_mild_rough_config(self) -> None:
        spec = load_spec_from_config(config_dir() / "mild_rough_velocity.json")
        self.assertEqual(spec.terrain, "mild_rough")
        spec.validate()

    def test_obs_blocks_cover_full_vector(self) -> None:
        spec = load_spec_from_config(config_dir() / "flat_velocity.json")
        blocks = spec.obs_block_offsets
        self.assertEqual(blocks[-1][2], OBS_DIM)
        self.assertEqual(blocks[0][0], "base_lin_vel")
        self.assertEqual(blocks[3][0], "cmd_vel")


if __name__ == "__main__":
    unittest.main()

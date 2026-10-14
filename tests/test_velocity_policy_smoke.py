"""CI smoke: dummy export + short policy rollout (no GPU)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from ohho_go2.policy.dummy_policy import (  # noqa: E402
    forward,
    load_weights,
    make_dummy_weights,
    run_steps,
)
from ohho_go2.policy.export_stub import write_export_bundle  # noqa: E402
from ohho_go2.policy.spec import (  # noqa: E402
    ACTION_DIM,
    OBS_DIM,
    config_dir,
    load_spec_from_config,
)


class TestVelocityPolicySmoke(unittest.TestCase):
    def test_dummy_forward_shape(self) -> None:
        weights = make_dummy_weights(seed=1)
        obs = [0.0] * OBS_DIM
        action = forward(obs, weights)
        self.assertEqual(len(action), ACTION_DIM)

    def test_run_five_steps(self) -> None:
        weights = make_dummy_weights(seed=2)
        actions = run_steps(weights, 5)
        self.assertEqual(len(actions), 5)
        for row in actions:
            self.assertEqual(len(row), ACTION_DIM)

    def test_export_bundle_manifest_fields(self) -> None:
        spec = load_spec_from_config(config_dir() / "flat_velocity.json")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            paths = write_export_bundle(out, spec, seed=99, licence="Apache-2.0")
            manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
            self.assertEqual(manifest["licence"], "Apache-2.0")
            self.assertEqual(manifest["seed"], 99)
            self.assertIn("reward_curve", manifest)
            weights = load_weights(paths["weights"])
            action = forward([0.0] * OBS_DIM, weights)
            self.assertEqual(len(action), ACTION_DIM)


if __name__ == "__main__":
    unittest.main()

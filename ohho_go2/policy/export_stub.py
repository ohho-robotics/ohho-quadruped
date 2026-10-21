"""Export manifest + dummy weights; documents ONNX/TorchScript path for humans."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ohho_go2.policy.dummy_policy import make_dummy_weights
from ohho_go2.policy.spec import JOINT_NAMES, VelocityPolicySpec


@dataclass
class ExportManifest:
    format: str
    spec_version: str
    terrain: str
    licence: str
    seed: int
    reward_curve: dict[str, Any]
    obs_dim: int
    action_dim: int
    joint_names: tuple[str, ...]
    obs_blocks: list[dict[str, float | int | str]]
    export_notes: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def manifest_from_spec(spec: VelocityPolicySpec, *, seed: int, licence: str) -> ExportManifest:
    blocks = [
        {"name": name, "start": start, "end": end, "scale": scale}
        for name, start, end, scale in spec.obs_block_offsets
    ]
    return ExportManifest(
        format="dummy_linear_json",
        spec_version=spec.spec_version,
        terrain=spec.terrain,
        licence=licence,
        seed=seed,
        reward_curve={
            "status": "placeholder",
            "description": "Replace with training log path or JSON after GPU run",
            "final_episodic_reward": None,
        },
        obs_dim=spec.obs_dim,
        action_dim=spec.action_dim,
        joint_names=JOINT_NAMES,
        obs_blocks=blocks,
        export_notes=(
            "After real train: torch.onnx.export(...) -> policy.onnx or "
            "torch.jit.trace -> policy.pt; update format field."
        ),
    )


def write_export_bundle(
    out_dir: Path,
    spec: VelocityPolicySpec,
    *,
    seed: int = 42,
    licence: str = "Apache-2.0",
) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = manifest_from_spec(spec, seed=seed, licence=licence)
    manifest_path = out_dir / "manifest.json"
    weights_path = out_dir / "dummy_policy_weights.json"
    onnx_stub_path = out_dir / "export_stub.onnx.txt"

    weights = make_dummy_weights(seed=seed)
    weights_path.write_text(json.dumps(weights, indent=2), encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest.to_dict(), indent=2), encoding="utf-8")
    onnx_stub_path.write_text(
        "# ONNX export not run in CI.\n"
        "# Human: export trained policy to policy.onnx and update manifest.format.\n",
        encoding="utf-8",
    )
    return {
        "manifest": manifest_path,
        "weights": weights_path,
        "onnx_stub": onnx_stub_path,
    }

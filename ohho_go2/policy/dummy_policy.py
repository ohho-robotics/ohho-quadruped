"""Tiny linear policy for CI smoke (no torch/onnx required)."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from ohho_go2.policy.spec import ACTION_DIM, OBS_DIM


def _zeros(rows: int, cols: int) -> list[list[float]]:
    return [[0.0 for _ in range(cols)] for _ in range(rows)]


def make_dummy_weights(seed: int = 0) -> dict[str, Any]:
    """Deterministic small weights: action_i ~= 0.01 * tanh(obs_i)."""
    # Simple fixed matrix from seed (LCG) for reproducibility without numpy.
    state = seed & 0xFFFFFFFF
    weight = _zeros(ACTION_DIM, OBS_DIM)
    for i in range(ACTION_DIM):
        for j in range(OBS_DIM):
            state = (state * 1664525 + 1013904223) & 0xFFFFFFFF
            weight[i][j] = ((state / 0xFFFFFFFF) - 0.5) * 0.002
    bias = [0.0] * ACTION_DIM
    return {"seed": seed, "weight": weight, "bias": bias}


def forward(obs: list[float], weights: dict[str, Any]) -> list[float]:
    if len(obs) != OBS_DIM:
        raise ValueError(f"obs must have length {OBS_DIM}")
    w = weights["weight"]
    b = weights["bias"]
    out: list[float] = []
    for i in range(ACTION_DIM):
        acc = float(b[i])
        row = w[i]
        for j, v in enumerate(obs):
            acc += row[j] * v
        out.append(math.tanh(acc))
    return out


def run_steps(
    weights: dict[str, Any],
    steps: int,
    *,
    cmd_vel: tuple[float, float, float] = (0.3, 0.0, 0.0),
) -> list[list[float]]:
    """Run a short open-loop smoke rollout (obs cmd_vel slots only)."""
    obs = [0.0] * OBS_DIM
    obs[9], obs[10], obs[11] = cmd_vel
    actions: list[list[float]] = []
    for _ in range(steps):
        action = forward(obs, weights)
        actions.append(action)
        # Feed last_action block; leave other obs static for smoke.
        for k, a in enumerate(action):
            obs[36 + k] = a
    return actions


def load_weights(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "weight" not in data or "bias" not in data:
        raise ValueError("weights file missing weight/bias")
    return data

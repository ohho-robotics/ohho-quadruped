"""JSON metrics artifact for MuJoCo smoke CI (OHH-124)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass
class SmokeReport:
    schema: str = "ohho-mujoco-smoke-v1"
    issue: str = "OHH-124"
    timestamp_utc: str = field(
        default_factory=lambda: datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    unittest: dict[str, Any] = field(default_factory=dict)
    dds_sim: dict[str, Any] = field(default_factory=dict)
    sport_shim: dict[str, Any] = field(default_factory=dict)
    office_scene: dict[str, Any] = field(default_factory=dict)
    mp4: dict[str, Any] = field(
        default_factory=lambda: {
            "status": "skipped",
            "reason": "offscreen render not wired in CI",
        }
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def write_report(path: Path, report: SmokeReport) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")

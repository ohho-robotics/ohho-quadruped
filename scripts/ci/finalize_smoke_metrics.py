#!/usr/bin/env python3
"""Write mujoco-smoke-metrics.json from environment (OHH-124)."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

# `python scripts/ci/finalize_smoke_metrics.py` puts scripts/ci on sys.path, not the repo root.
_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from ohho_go2.smoke.metrics import SmokeReport, write_report  # noqa: E402


def main() -> int:
    repo = Path(os.environ.get("REPO_ROOT", ".")).resolve()
    default_metrics = repo / "artifacts/mujoco-smoke-metrics.json"
    metrics_file = Path(os.environ.get("METRICS_FILE", str(default_metrics)))
    unittest_rc = int(os.environ.get("UNITTEST_RC", "1"))
    dds_status = os.environ.get("DDS_STATUS", "skipped")
    dds_exit = os.environ.get("DDS_EXIT_CODE")

    dds_sim: dict[str, object] = {"status": dds_status}
    if dds_status == "passed":
        dds_sim.update({"mode": "headless_xvfb", "domain_id": 1, "interface": "lo"})
    elif dds_status == "failed" and dds_exit is not None:
        dds_sim["exit_code"] = int(dds_exit)
    elif dds_status == "skipped":
        reason = os.environ.get("DDS_SKIP_REASON", "not run")
        dds_sim["reason"] = reason

    sport_status = os.environ.get("SPORT_SHIM_STATUS", "").strip()
    sport_reason = os.environ.get("SPORT_SHIM_REASON", "").strip()
    if sport_status:
        sport_shim: dict[str, str] = {"status": sport_status}
        if sport_reason:
            sport_shim["reason"] = sport_reason
    elif importlib.util.find_spec("ohho_go2.sport_shim"):
        sport_shim = {
            "status": "skipped",
            "reason": "sport_shim module present; run scripts/ci/run-mujoco-smoke.sh to execute it",
        }
    else:
        sport_shim = {
            "status": "skipped",
            "reason": "OHH-123 sport shim is not in this checkout (quadruped PR #8)",
        }

    office_scene: dict[str, str]
    # Main's sim layout names OhhO scenes sim/scenes/<scene>_env.xml (OHH-121).
    office_rel = "sim/scenes/office_env.xml"
    if (repo / office_rel).is_file():
        office_scene = {"status": "present", "path": office_rel}
    else:
        office_scene = {
            "status": "missing",
            "reason": f"{office_rel} not added; unitree_mujoco default Go2 scene",
        }

    report = SmokeReport(
        unittest={
            "status": "passed" if unittest_rc == 0 else "failed",
            "exit_code": unittest_rc,
        },
        dds_sim=dds_sim,
        sport_shim=sport_shim,
        office_scene=office_scene,
    )
    write_report(metrics_file, report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

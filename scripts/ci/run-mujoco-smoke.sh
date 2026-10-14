#!/usr/bin/env bash
# run-mujoco-smoke.sh — unittest smoke contract + optional headless unitree_mujoco DDS check.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
UNITREE_WS="${UNITREE_WS:-$HOME/unitree}"
METRICS_DIR="${METRICS_DIR:-$REPO_ROOT/artifacts}"
METRICS_FILE="${METRICS_FILE:-$METRICS_DIR/mujoco-smoke-metrics.json}"
RUN_FULL_DDS="${OHHO_MUJOCO_SMOKE_DDS:-1}"

mkdir -p "$METRICS_DIR"

if [ -f "$UNITREE_WS/env.sh" ]; then
  # shellcheck disable=SC1091
  . "$UNITREE_WS/env.sh"
fi

PY="python3"
if command -v python >/dev/null 2>&1; then
  PY="python"
elif [ -x "$UNITREE_WS/venv/bin/python" ]; then
  PY="$UNITREE_WS/venv/bin/python"
fi

cd "$REPO_ROOT"
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"

echo "== MuJoCo smoke: unittest contract (mock-backed)"
set +e
UNITTEST_OUT="$("$PY" -m unittest discover -s tests -p 'test_mujoco_smoke.py' -v 2>&1)"
UNITTEST_RC=$?
set -e
echo "$UNITTEST_OUT"

# Sport shim is implemented on quadruped PR #8 (branch ohh-123-sport-shim).
# This job runs those headless tests when the module is in the tree.
SPORT_SHIM_STATUS="skipped"
SPORT_SHIM_REASON="OHH-123 sport shim is not in this checkout (quadruped PR #8)"
SPORT_SHIM_RC=0
if [ -f "$REPO_ROOT/ohho_go2/sport_shim.py" ] && [ -f "$REPO_ROOT/tests/test_sport_shim.py" ]; then
  echo "== MuJoCo smoke: sport shim headless tests (OHH-123 / PR #8)"
  set +e
  "$PY" -m unittest discover -s tests -p 'test_sport_shim.py' -v
  SPORT_SHIM_RC=$?
  set -e
  if [ "$SPORT_SHIM_RC" -eq 0 ]; then
    SPORT_SHIM_STATUS="passed"
    SPORT_SHIM_REASON=""
  else
    SPORT_SHIM_STATUS="failed"
    SPORT_SHIM_REASON="tests/test_sport_shim.py exit ${SPORT_SHIM_RC}"
  fi
fi

DDS_STATUS="skipped"
DDS_EXIT_CODE=""
DDS_SKIP_REASON=""
if [ "$RUN_FULL_DDS" = "1" ] && [ -f "$UNITREE_WS/env.sh" ]; then
  echo "== MuJoCo smoke: headless unitree_mujoco DDS (domain 1, lo)"
  set +e
  DDS_OUT="$(bash "$REPO_ROOT/scripts/dev/smoke-unitree-sim.sh" 2>&1)"
  DDS_RC=$?
  set -e
  echo "$DDS_OUT"
  if [ "$DDS_RC" -eq 0 ]; then
    DDS_STATUS="passed"
  else
    DDS_STATUS="failed"
    DDS_EXIT_CODE="$DDS_RC"
  fi
elif [ ! -f "$UNITREE_WS/env.sh" ]; then
  DDS_SKIP_REASON="unitree stack not installed (no env.sh)"
else
  DDS_SKIP_REASON="OHHO_MUJOCO_SMOKE_DDS=0"
fi

export METRICS_FILE UNITTEST_RC DDS_STATUS DDS_EXIT_CODE DDS_SKIP_REASON REPO_ROOT
export SPORT_SHIM_STATUS SPORT_SHIM_REASON
"$PY" "$REPO_ROOT/scripts/ci/finalize_smoke_metrics.py"

if [ "$UNITTEST_RC" -ne 0 ]; then
  exit "$UNITTEST_RC"
fi
if [ "$SPORT_SHIM_RC" -ne 0 ]; then
  exit "$SPORT_SHIM_RC"
fi
if [ "$RUN_FULL_DDS" = "1" ] && [ -f "$UNITREE_WS/env.sh" ] && [ "$DDS_STATUS" != "passed" ]; then
  exit 1
fi

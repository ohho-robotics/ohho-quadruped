#!/usr/bin/env bash
# smoke-unitree-sim.sh - end-to-end check of the Unitree sim stack set up by setup-unitree-wsl.sh.
#
# 1. Starts unitree_mujoco's simulate_python/unitree_mujoco.py (Go2, DOMAIN_ID=1, INTERFACE=lo,
#    USE_JOYSTICK=0) - headless under Xvfb by default.
# 2. Runs unitree_mujoco's simulate_python/test/test_unitree_sdk2.py, which subscribes to
#    rt/lowstate (LowState_) and rt/sportmodestate (SportModeState_) over DDS domain 1 on lo.
# 3. Passes if both messages print, then stops everything.
#
# Simulation only: test_unitree_sdk2.py also publishes rt/lowcmd (1 Nm on each joint) to the sim.
# Never point this at a real robot interface.
#
# Usage:
#   bash scripts/dev/smoke-unitree-sim.sh
# Environment:
#   UNITREE_WS=~/unitree   same value used for setup (default: $HOME/unitree)
#   HEADLESS=0             show the MuJoCo viewer through WSLg instead of Xvfb
#   SIM_WARMUP=8           seconds to let the sim come up before subscribing
#   LISTEN_SECONDS=5       how long the subscriber runs

set -euo pipefail

UNITREE_WS="${UNITREE_WS:-$HOME/unitree}"
HEADLESS="${HEADLESS:-1}"
SIM_WARMUP="${SIM_WARMUP:-8}"
LISTEN_SECONDS="${LISTEN_SECONDS:-5}"

if [ ! -f "$UNITREE_WS/env.sh" ]; then
  echo "missing $UNITREE_WS/env.sh - run scripts/dev/setup-unitree-wsl.sh first" >&2
  exit 2
fi
# shellcheck disable=SC1091
. "$UNITREE_WS/env.sh"

SIM_DIR="$UNITREE_WS/unitree_mujoco/simulate_python"
LOG_DIR="$(mktemp -d /tmp/ohho-smoke.XXXXXX)"
SIM_LOG="$LOG_DIR/sim.log"
SUB_LOG="$LOG_DIR/subscriber.log"

echo "== $(date -Iseconds) smoke test"
grep -E '^(ROBOT|DOMAIN_ID|INTERFACE|USE_JOYSTICK) =' "$SIM_DIR/config.py"

cd "$SIM_DIR"
if [ "$HEADLESS" = "1" ]; then
  echo "== starting unitree_mujoco headless (Xvfb)"
  setsid xvfb-run -a -s "-screen 0 1280x720x24" python -u unitree_mujoco.py >"$SIM_LOG" 2>&1 &
else
  echo "== starting unitree_mujoco with viewer on DISPLAY=${DISPLAY:-unset}"
  setsid python -u unitree_mujoco.py >"$SIM_LOG" 2>&1 &
fi
SIM_PID=$!
cleanup() { kill -- "-$SIM_PID" 2>/dev/null || true; wait "$SIM_PID" 2>/dev/null || true; }
trap cleanup EXIT

sleep "$SIM_WARMUP"
if ! kill -0 "$SIM_PID" 2>/dev/null; then
  echo "FAIL: simulator exited early. Log:" >&2
  cat "$SIM_LOG" >&2
  exit 1
fi
echo "== simulator up (pid $SIM_PID); first lines of its log:"
head -n 12 "$SIM_LOG"

echo "== running test/test_unitree_sdk2.py for ${LISTEN_SECONDS}s"
(cd test && timeout "$LISTEN_SECONDS" python -u test_unitree_sdk2.py >"$SUB_LOG" 2>&1) || true

# The two subscriber callbacks print from different threads, so lines can interleave;
# count the markers anywhere on a line.
# grep exits 1 on no match; keep that from tripping set -e/pipefail so the FAIL branch runs.
LOW=$({ grep -o 'IMU state:' "$SUB_LOG" || true; } | wc -l)
HIGH=$({ grep -o 'Position:' "$SUB_LOG" || true; } | wc -l)
echo "== LowState (rt/lowstate) messages: $LOW"
grep -m 1 'IMUState_(' "$SUB_LOG" | cut -c1-500 || true
echo "== SportModeState (rt/sportmodestate) messages: $HIGH"
grep -m 3 '^Position:' "$SUB_LOG" || true

if [ "$LOW" -gt 0 ] && [ "$HIGH" -gt 0 ]; then
  echo "PASS: Go2 LowState and SportModeState received over DDS domain 1 on lo (logs: $LOG_DIR)"
else
  echo "FAIL: missing state messages. Subscriber log tail:" >&2
  tail -n 30 "$SUB_LOG" >&2
  exit 1
fi

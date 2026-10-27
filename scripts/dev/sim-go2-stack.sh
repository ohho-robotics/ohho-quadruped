#!/usr/bin/env bash
# Start MuJoCo + the Go2 sport server + ohho sim-serve for local /sim.
#
# Domain 1, interface lo only. This is a simulator. Do not point it at a robot.
#
# Usage (inside WSL, from anywhere):
#   export OHHO_OS=/path/to/ohho-os
#   bash scripts/dev/sim-go2-stack.sh
#
# The console connects to ws://127.0.0.1:8765 (forwarded from WSL to Windows).
# OHHO_OS is the ohho-os checkout that contains ohho/cli.py.
# UNITREE_ENV defaults to /opt/unitree/env.sh.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
UNITREE_ENV="${UNITREE_ENV:-/opt/unitree/env.sh}"
OHHO_OS="${OHHO_OS:-}"

if [ -z "$OHHO_OS" ] || [ ! -f "$OHHO_OS/ohho/cli.py" ]; then
  echo "Set OHHO_OS to an ohho-os checkout (it must contain ohho/cli.py)." >&2
  exit 2
fi
if [ ! -f "$UNITREE_ENV" ]; then
  echo "missing $UNITREE_ENV — run scripts/dev/setup-unitree-wsl.sh first." >&2
  exit 2
fi

# shellcheck disable=SC1090
. "$UNITREE_ENV"
export MUJOCO_GL="${MUJOCO_GL:-egl}"
export PYTHONPATH="$OHHO_OS${PYTHONPATH:+:$PYTHONPATH}"

if ! python -c 'import websockets' >/dev/null 2>&1; then
  echo "sim-serve needs websockets in this Python. In the Unitree venv: pip install websockets" >&2
  exit 2
fi

cd "$ROOT"
python sim/run_go2.py --headless --no-joystick --domain 1 --iface lo &
SIM_PID=$!
python -m ohho_go2.dds_server --domain 1 --interface lo &
SHIM_PID=$!
python -c 'from ohho.cli import main; raise SystemExit(main())' \
  sim-serve --backend robot --robot unitree-go2 --transport 'dds://lo?domain=1' &
SERVE_PID=$!

cleanup() {
  kill "$SERVE_PID" "$SHIM_PID" "$SIM_PID" 2>/dev/null || true
  wait "$SERVE_PID" "$SHIM_PID" "$SIM_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "MuJoCo pid $SIM_PID, sport server pid $SHIM_PID, sim-serve pid $SERVE_PID"
echo "Console sim-serve URL: ws://127.0.0.1:8765"
while kill -0 "$SIM_PID" 2>/dev/null && kill -0 "$SHIM_PID" 2>/dev/null && kill -0 "$SERVE_PID" 2>/dev/null; do
  sleep 1
done
echo "A stack process exited. Stopping the others." >&2
exit 1

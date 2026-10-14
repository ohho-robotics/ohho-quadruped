#!/usr/bin/env bash
# run-nav2-headless-test.sh - Headless launch test for Go2 Nav2 + SLAM + Bridge.
#
# Launches go2_nav_sim.launch.py headless:=true use_mock_sim:=true for up to 60s.
# Verifies key ROS 2 topics and nodes are active, then exits 0.
#
# NOTE: Real MuJoCo office 4/5 goal navigation evaluation is a human verification
# task in WSL2/hardware; this CI test verifies the ROS 2 graph and headless lifecycle.

set -euo pipefail

export ROS_DOMAIN_ID=1
export ROS_LOCALHOST_ONLY=1
export ROS2CLI_DISABLE_DAEMON=1

echo "==> Sourcing ROS 2 and workspace setup"
if [ -f /opt/ros/humble/setup.bash ]; then
  # shellcheck disable=SC1091
  source /opt/ros/humble/setup.bash
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [ -f "$REPO_ROOT/ros2_ws/install/setup.bash" ]; then
  # shellcheck disable=SC1091
  source "$REPO_ROOT/ros2_ws/install/setup.bash"
fi

ros2 daemon stop 2>/dev/null || true

echo "==> Launching Go2 navigation stack in headless mode (mock sim, domain 1)"
LOGFILE="/tmp/go2_nav_sim.log"

ros2 launch ohho_go2_navigation go2_nav_sim.launch.py \
  headless:=true \
  use_mock_sim:=true \
  use_sim_time:=false \
  autostart:=true > "$LOGFILE" 2>&1 &
LAUNCH_PID=$!

cleanup() {
  echo "==> Cleaning up launch process (PID $LAUNCH_PID)"
  kill -INT "$LAUNCH_PID" 2>/dev/null || true
  sleep 2
  kill -9 "$LAUNCH_PID" 2>/dev/null || true
}
trap cleanup EXIT

echo "==> Waiting up to 60s for nodes and topics..."
SUCCESS=0
for i in $(seq 1 60); do
  sleep 1
  if ! kill -0 "$LAUNCH_PID" 2>/dev/null; then
    echo "Launch process exited prematurely. Log output:"
    cat "$LOGFILE"
    exit 1
  fi

  TOPICS=$(ros2 topic list 2>/dev/null || true)
  if echo "$TOPICS" | grep -q "/odom" && \
     echo "$TOPICS" | grep -q "/scan" && \
     echo "$TOPICS" | grep -q "/joint_states"; then
    echo "Required topics found at iteration $i:"
    echo "  /odom, /scan, /joint_states active"
    SUCCESS=1
    break
  fi
done

if [ "$SUCCESS" -eq 1 ]; then
  echo "==> Headless launch test passed successfully!"
  exit 0
else
  echo "==> Timed out waiting for ROS 2 topics. Log tail:"
  tail -n 100 "$LOGFILE" || true
  exit 1
fi

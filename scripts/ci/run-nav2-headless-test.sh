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
# Humble setup.bash reads unset AMENT_* variables; nounset would abort the test.
set +u
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
set -u

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

echo "==> Waiting up to 60s for topics, slam_toolbox, and active Nav2 lifecycle nodes..."
SUCCESS=0
QUERY_TIMEOUT_SEC=5
STACK_DEADLINE_SEC=60
deadline=$((SECONDS + STACK_DEADLINE_SEC))

# Bound every CLI call. Humble `ros2 lifecycle get` waits forever when a
# service is advertised but does not answer, which would skip the deadline.
ros2_bounded() {
  local remaining=$((deadline - SECONDS))
  local limit="$QUERY_TIMEOUT_SEC"
  if [ "$remaining" -le 0 ]; then
    return 0
  fi
  if [ "$remaining" -lt "$limit" ]; then
    limit=$remaining
  fi
  timeout "$limit" "$@" 2>/dev/null || true
}

# Topics from the sim sensor node are not enough: slam_toolbox must be running
# and each Nav2 lifecycle server must be active.
stack_ready() {
  local topics nodes name state
  if [ "$SECONDS" -ge "$deadline" ]; then
    return 1
  fi
  topics=$(ros2_bounded ros2 topic list)
  echo "$topics" | grep -qx "/odom" || return 1
  echo "$topics" | grep -qx "/scan" || return 1
  echo "$topics" | grep -qx "/joint_states" || return 1

  nodes=$(ros2_bounded ros2 node list)
  echo "$nodes" | grep -qx "/slam_toolbox" || return 1

  for name in \
    controller_server \
    smoother_server \
    planner_server \
    behavior_server \
    bt_navigator \
    waypoint_follower
  do
    echo "$nodes" | grep -qx "/${name}" || return 1
    state=$(ros2_bounded ros2 lifecycle get "/${name}")
    # Match the state word only. "inactive" must not count as active.
    echo "$state" | grep -qiw "active" || return 1
  done
}
iteration=0
while [ "$SECONDS" -lt "$deadline" ]; do
  iteration=$((iteration + 1))
  sleep 1
  if ! kill -0 "$LAUNCH_PID" 2>/dev/null; then
    echo "Launch process exited prematurely. Log output:"
    cat "$LOGFILE"
    exit 1
  fi

  if stack_ready; then
    echo "Required topics, slam_toolbox, and active Nav2 lifecycle nodes at iteration $iteration"
    SUCCESS=1
    break
  fi
done

if [ "$SUCCESS" -eq 1 ]; then
  echo "==> Headless launch test passed successfully!"
  exit 0
else
  echo "==> Timed out waiting for topics, slam_toolbox, or active Nav2 lifecycle nodes. Log tail:"
  tail -n 100 "$LOGFILE" || true
  exit 1
fi

#!/usr/bin/env bash
# check-go2-description.sh — URDF parse and launch --show-args for go2_description.
#
# Gazebo Harmonic headless spawn is a local check, not this script.
# See docs/evidence/ohh-65.md.

set -euo pipefail

echo "==> Sourcing ROS 2 and workspace setup"
# ROS setup.bash reads unset AMENT_* variables; nounset would abort the check.
set +u
if [ -f /opt/ros/jazzy/setup.bash ]; then
  # shellcheck disable=SC1091
  source /opt/ros/jazzy/setup.bash
elif [ -f /opt/ros/humble/setup.bash ]; then
  # shellcheck disable=SC1091
  source /opt/ros/humble/setup.bash
else
  echo "No ROS setup.bash found" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [ ! -f "$REPO_ROOT/ros2_ws/install/setup.bash" ]; then
  echo "ros2_ws/install/setup.bash is missing; colcon build go2_description first" >&2
  exit 1
fi
# shellcheck disable=SC1091
source "$REPO_ROOT/ros2_ws/install/setup.bash"
set -u

export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-1}"
export ROS_LOCALHOST_ONLY="${ROS_LOCALHOST_ONLY:-1}"
export ROS2CLI_DISABLE_DAEMON=1
ros2 daemon stop 2>/dev/null || true

DESC="$REPO_ROOT/ros2_ws/src/go2_description"
URDF="$DESC/urdf/go2_description.urdf"

echo "==> check_urdf shipped model"
check_urdf "$URDF"

for pose in standing lying; do
  echo "==> check_urdf spawn pose: $pose"
  python3 "$DESC/launch/spawn_pose.py" --pose "$pose" --urdf "$URDF" --out "/tmp/go2_${pose}_spawn.urdf"
  check_urdf "/tmp/go2_${pose}_spawn.urdf"
done

echo "==> xacro robot.xacro then check_urdf"
xacro "$DESC/xacro/robot.xacro" -o /tmp/go2_from_xacro.urdf
check_urdf /tmp/go2_from_xacro.urdf

echo "==> ros2 launch --show-args"
ros2 launch go2_description display.launch.py --show-args
ros2 launch go2_description gazebo.launch.py --show-args

echo "==> go2_description URDF and launch args checked"

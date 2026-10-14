#!/usr/bin/env bash
# install-humble-ws-deps.sh - Install ros2_ws package dependencies via rosdep (Humble).
#
# Run after ros-tooling/setup-ros so duplicate ROS apt list files can be deduped safely.

set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

bash "$SCRIPT_DIR/prepare-ros-apt-for-gha.sh"
sudo apt-get update -qq

# shellcheck disable=SC1091
source /opt/ros/humble/setup.bash

echo "==> Updating rosdep database"
rosdep update

echo "==> Installing workspace dependencies from package.xml (rosdep)"
cd "$REPO_ROOT/ros2_ws"
rosdep install --from-paths src --ignore-src -y -r --rosdistro humble

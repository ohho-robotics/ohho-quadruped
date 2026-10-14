#!/usr/bin/env bash
# install-humble-ws-deps.sh - Install ros2_ws package dependencies via rosdep (Humble).

set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# shellcheck disable=SC1091
source /opt/ros/humble/setup.bash

echo "==> Updating rosdep database"
rosdep update

echo "==> Installing workspace dependencies from package.xml (rosdep)"
cd "$REPO_ROOT/ros2_ws"
rosdep install --from-paths src --ignore-src -y -r --rosdistro humble

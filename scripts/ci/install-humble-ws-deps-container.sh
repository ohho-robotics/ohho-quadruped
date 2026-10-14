#!/usr/bin/env bash
# install-humble-ws-deps-container.sh - rosdep install inside ros:humble-ros-base-jammy (CI).
#
# Avoids apt conflicts from setup-ros on GitHub-hosted ubuntu-22.04 runners when
# installing Nav2 binary packages.

set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

apt-get update -qq
apt-get install -y -qq --no-install-recommends \
  python3-colcon-common-extensions \
  python3-rosdep

# shellcheck disable=SC1091
source /opt/ros/humble/setup.bash

rosdep update
cd "$REPO_ROOT/ros2_ws"
rosdep install --from-paths src --ignore-src -y -r --rosdistro humble

#!/usr/bin/env bash
# install-humble-ws-deps.sh - Nav2 + SLAM apt deps on setup-ros runners.
#
# Same package set as install-humble-ws-deps-container.sh, with apt source dedupe after setup-ros.

set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

bash "$SCRIPT_DIR/prepare-ros-apt-for-gha.sh"
sudo apt-get update -qq
sudo apt-get install -y -qq --no-install-recommends \
  ros-humble-ament-cmake \
  ros-humble-nav2-bringup \
  ros-humble-nav2-smoother \
  ros-humble-nav2-behaviors \
  ros-humble-nav2-waypoint-follower \
  ros-humble-slam-toolbox \
  ros-humble-robot-state-publisher \
  ros-humble-joint-state-publisher \
  ros-humble-xacro \
  ros-humble-rviz2

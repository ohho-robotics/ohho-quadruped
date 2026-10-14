#!/usr/bin/env bash
# prepare-ros-apt-for-gha.sh - Avoid duplicate ROS apt sources on GitHub-hosted runners.
#
# ubuntu-22.04 images may ship ros-latest.list while setup-ros adds ros2-latest.list.
# Duplicate entries cause apt resolver failures when installing Nav2 (held broken packages).

set -euo pipefail

if [[ -f /etc/apt/sources.list.d/ros-latest.list && -f /etc/apt/sources.list.d/ros2-latest.list ]]; then
  echo "==> Removing duplicate /etc/apt/sources.list.d/ros-latest.list (keep ros2-latest.list)"
  sudo rm -f /etc/apt/sources.list.d/ros-latest.list
fi

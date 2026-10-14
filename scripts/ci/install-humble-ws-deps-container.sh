#!/usr/bin/env bash
# install-humble-ws-deps-container.sh - Nav2 + SLAM apt deps inside ros:humble-ros-base-jammy.
#
# Uses explicit binary packages (not the navigation2 metapackage) to avoid apt resolver
# conflicts on GitHub-hosted runners. Local workspace packages are built with colcon.

set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

apt-get update -qq
apt-get install -y -qq --no-install-recommends \
  python3-colcon-common-extensions \
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

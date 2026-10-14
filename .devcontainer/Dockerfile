# ROS 2 Humble dev image for ohho_go2_bridge (no Unitree SDK in image).
FROM ros:humble-ros-base-jammy

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    python3-colcon-common-extensions \
    ros-humble-rmw-cyclonedds-cpp \
    && rm -rf /var/lib/apt/lists/*

ENV ROS_DOMAIN_ID=1
WORKDIR /workspace

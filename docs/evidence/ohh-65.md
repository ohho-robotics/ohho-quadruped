# OHH-65 evidence

Sim only, no gait controller. Nothing in this note was run on hardware.

## Already on the stacked description branch

- `ros2_ws/src/go2_description/` URDF, meshes, xacro (including upstream `xacro/gazebo.xacro`), RViz config, and `launch/display.launch.py`
- Humble colcon build of `go2_description` in `.github/workflows/ros2-nav2.yml`
- BSD-3-Clause licence kept at `ros2_ws/src/go2_description/LICENSE`, with the upstream attribution in that package README

## Added here

- `launch/gazebo.launch.py` and `launch/spawn_pose.py`: ROS 2 Jazzy + Gazebo Harmonic via `ros_gz_sim` `create` and `robot_state_publisher`. The spawn is a static visual, `pose:=standing` or `pose:=lying`. No gait controller. Upstream classic `xacro/gazebo.xacro` plugins are not loaded.
- `launch/display.launch.py`: optional `use_joint_state_publisher_gui` when `use_bridge_joint_states:=false`
- Existing `nav2-headless-launch-test` job runs `scripts/ci/check-go2-description.sh` (`check_urdf`, `xacro` then `check_urdf`, and `ros2 launch --show-args` for both launch files)

## Local run (2026-10-14)

Image: `omnibot-nav-dev:latest` (ROS 2 Jazzy, Gazebo Harmonic `gz sim` 8.15.0). Environment: `ROS_DOMAIN_ID=1`, `ROS_LOCALHOST_ONLY=1`.

- `colcon build --packages-select go2_description` finished (about 1s)
- `check_urdf` on `urdf/go2_description.urdf`: parsed (`robot name is: go2_description`)
- Spawn URDF standing: `xyz 0 0 0.2848`, `check_urdf` parsed
- Spawn URDF lying: `xyz 0 0 0.1620`, roll `1.5708`, `check_urdf` parsed
- `xacro xacro/robot.xacro` then `check_urdf`: parsed (`robot name is: go2`)
- `ros2 launch go2_description display.launch.py --show-args` listed `use_joint_state_publisher_gui` (default `false`)
- `ros2 launch go2_description gazebo.launch.py --show-args` listed `pose` (default `standing`) and `gui`
- Headless `gui:=false` standing spawn: log line `[spawn_go2]: Entity creation successful.` `gz model --list` showed `ground_plane` and `go2` (about 3s)
- Headless lying spawn: same entity result (about 2s). Log line: `go2 visual spawn pose=lying xyz=(0.000,0.000,0.162) rpy=(1.571,0.000,0.000) static, no gait controller`

The captured spawn logs did not report a mesh-load error. A windowed `ros2 launch go2_description gazebo.launch.py` still needs a display; this run used `gui:=false`.

## CI scope

The Humble job checks URDF parse and launch arguments. It does not start Gazebo Harmonic. The headless spawn above is the local check.

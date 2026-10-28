# go2_description

URDF and mesh description package for the Unitree Go2 quadruped robot.

**Sim only, no gait controller.** RViz and the Gazebo Harmonic spawn show the model. They do not start a gait, ros2_control, or hardware.

Vendored from [unitreerobotics/unitree_ros](https://github.com/unitreerobotics/unitree_ros) under the **BSD 3-Clause License** (see [LICENSE](LICENSE)).

## Contents

- `urdf/go2_description.urdf` — Kinematic model with 12 leg joints, base_link, radar, and camera frames
- `meshes/` — Visual and collision meshes in COLLADA (`.dae`) format
- `launch/display.launch.py` — Robot state publisher and RViz2 visualization
- `launch/gazebo.launch.py` — Static visual spawn in Gazebo Harmonic (`standing` or `lying`)
- `xacro/gazebo.xacro` — Upstream classic Gazebo plugin file. `gazebo.launch.py` does not load it
- `rviz/go2.rviz` — RViz2 configuration

## Usage

```bash
cd ros2_ws
colcon build --packages-select go2_description
source install/setup.bash
ros2 launch go2_description display.launch.py
```

By default, `robot_state_publisher` expects `/joint_states` from another node. `ohho_go2_bridge` declares the topic but does not publish samples yet. The sim-only sensor node in `ohho_go2_navigation` publishes it in Nav2 launches. To preview with offline joint states, or with the optional joint slider GUI:

```bash
ros2 launch go2_description display.launch.py use_bridge_joint_states:=false
ros2 launch go2_description display.launch.py use_bridge_joint_states:=false use_joint_state_publisher_gui:=true
```

Gazebo Harmonic (ROS 2 Jazzy, `ros_gz_sim`) spawn. Sim only, no gait controller. `pose:=standing` is upright; `pose:=lying` rolls the model onto its side. `gui:=false` runs the server without the Gazebo window.

```bash
ros2 launch go2_description gazebo.launch.py pose:=standing
ros2 launch go2_description gazebo.launch.py pose:=lying gui:=false
```

## ROS 1 references, not used by the ROS 2 stack

`config/robot_control.yaml`, `config/joint_names_go2_description.yaml`, and `xacro/` are vendored ROS 1 `gazebo_ros_control` references (`joint_state_controller`, `unitree_legged_control`, `libgazebo_ros_control.so`). No launch file in this repository loads them. They are not a ros2_control or Gazebo configuration for the ROS 2 packages.

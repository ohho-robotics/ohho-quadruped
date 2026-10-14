# go2_description

URDF and mesh description package for the Unitree Go2 quadruped robot.

Vendored from [unitreerobotics/unitree_ros](https://github.com/unitreerobotics/unitree_ros) under the **BSD 3-Clause License** (see [LICENSE](LICENSE)).

## Contents

- `urdf/go2_description.urdf` — Kinematic model with 12 leg joints, base_link, radar, and camera frames
- `meshes/` — Visual and collision meshes in COLLADA (`.dae`) format
- `launch/display.launch.py` — Robot state publisher and RViz2 visualization
- `rviz/go2.rviz` — RViz2 configuration

## Usage

```bash
cd ros2_ws
colcon build --packages-select go2_description
source install/setup.bash
ros2 launch go2_description display.launch.py
```

By default, `robot_state_publisher` expects `/joint_states` published by `ohho_go2_bridge`. To preview with offline joint sliders:

```bash
ros2 launch go2_description display.launch.py use_bridge_joint_states:=false
```

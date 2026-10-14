# ohho_go2_navigation

Navigation stack configuration (Nav2 + SLAM Toolbox) and simulation bringup for the Unitree Go2 quadruped.

## Overview

- **Robot footprint**: ~0.70m x 0.31m (`[[0.35, 0.155], [0.35, -0.155], [-0.35, -0.155], [-0.35, 0.155]]`)
- **Velocity limits**: Enforces SafetyGate limits (0.5 m/s forward, 0.3 m/s lateral, 1.0 rad/s yaw)
- **SLAM**: `slam_toolbox` online async mapping from `/scan`
- **Sim bringup**: `go2_nav_sim.launch.py` brings up description, the mock bridge, a sim-only kinematic sensor node, SLAM, and Nav2 in a single command

## Usage (ROS 2 Humble)

Ensure domain safety rules are respected (default `ROS_DOMAIN_ID=1` on loopback):

```bash
export ROS_DOMAIN_ID=1
cd ros2_ws
colcon build --packages-select go2_description ohho_go2_bridge ohho_go2_navigation
source install/setup.bash
```

### 1. View Robot Model in RViz
```bash
ros2 launch go2_description display.launch.py
```

### 2. All-in-One Navigation Simulation
```bash
ros2 launch ohho_go2_navigation go2_nav_sim.launch.py
```

Options:
- `headless:=true` — disables RViz2 (for CI and headless containers)
- `use_mock_sim:=true` — runs the sim-only kinematic sensor node (not hardware; MuJoCo is not required)
- `scene:=office` — MuJoCo environment scene (when `use_mock_sim:=false`)

## MuJoCo Office Evaluation Status

Office goal evaluation (e.g. 4/5 goals reached autonomously) is planned for verification in the WSL2 Unitree environment with MuJoCo simulator; it is a human verification task and not simulated in agent sessions.

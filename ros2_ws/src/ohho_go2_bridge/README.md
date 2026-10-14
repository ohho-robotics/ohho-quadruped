# ohho_go2_bridge

ROS 2 bridge scaffolding for the Unitree Go2 (Humble primary, Jazzy best-effort).
**Sim and mock only in CI** — no `unitree_ros2` dependency yet, no hardware commands.

## Topic mapping

See [docs/TOPIC_MAPPING.md](docs/TOPIC_MAPPING.md):

- `/cmd_vel` → sport `Move` with SafetyGate velocity caps and a **300 ms** `StopMove` watchdog
- `sportmodestate` → `/odom` + TF (stub until Unitree transport lands)
- `lowstate` → `/joint_states` + `/battery` (stub)
- `utlidar` cloud → `/scan` (stub)
- `/ohho/estop` (`std_msgs/Empty`) latched stop
- `/ohho/mode` (`std_msgs/String`) stand/lie allowlist

## Build (Humble)

```bash
export ROS_DOMAIN_ID=1
cd ros2_ws
colcon build --packages-select ohho_go2_bridge
source install/setup.bash
ros2 launch ohho_go2_bridge bridge.launch.py
```

Use the dev container (`.devcontainer/`) on Windows/WSL for a Humble toolchain without Unitree packages.

## Safety

- Default velocity caps match planned SafetyGate: 0.5 / 0.3 / 1.0 m/s and rad/s.
- `ROS_DOMAIN_ID=0` is refused unless `OHHO_ARM_HARDWARE=1` and an interactive TTY confirmation is provided.

## Tests

Root repo unittests (no colcon required):

```bash
python -m unittest discover -s tests
```

CI: [.github/workflows/ros2-bridge.yml](../../.github/workflows/ros2-bridge.yml).

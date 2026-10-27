# OhhO Go2 ROS 2 topic mapping

Scaffolding for `ohho_go2_bridge` (ROS 2 Humble primary, Jazzy best-effort).
No `unitree_ros2` dependency in this package yet; Unitree DDS topics are documented
for when the transport is wired.

## Intelligence layer (ROS) ↔ sport mode

| ROS topic / service | Message | Direction | Unitree / sport mapping |
|---|---|---|---|
| `/cmd_vel` | `geometry_msgs/Twist` | Subscribe | `Move(vx, vy, vyaw)` after SafetyGate-style velocity clamp; **300 ms** without a new message → `StopMove` |
| `/odom` | `nav_msgs/Odometry` | Publish | From `SportModeState` pose/twist (sportmodestate DDS) |
| TF `odom` → `base_link` | — | Broadcast | Same source as `/odom` |
| `/joint_states` | `sensor_msgs/JointState` | Publish | From `LowState` motor/joint positions |
| `/battery` | `sensor_msgs/BatteryState` | Publish | From `LowState` BMS SOC |
| `/scan` | `sensor_msgs/LaserScan` | Publish | From Unitree lidar point cloud (`utlidar` / cloud) projected to 2D scan |
| `/ohho/estop` | `std_msgs/Empty` | Subscribe | Latched stop: `StopMove` first; full stack adds human-only `release_stop` |
| `/ohho/mode` | `std_msgs/String` | Subscribe | Allowlisted stand/lie modes → `stand_up`, `stand_down`, `balance_stand`, `recovery_stand`, `sit`, `rise_sit` |

`Go2BridgeNode` implements the subscribe rows (`/cmd_vel`, `/ohho/estop`, `/ohho/mode`). The publish and broadcast rows (`/odom`, TF `odom` → `base_link`, `/joint_states`, `/battery`, `/scan`) are future mappings: this node declares those publishers and does not publish samples, and it creates no TF broadcaster. The sim-only sensor node in `ohho_go2_navigation` publishes that data in Nav2 launches.

## Unitree DDS topics (future transport)

| DDS / ROS (unitree_ros2) | Bridge use |
|---|---|
| `sportmodestate` | `/odom` + TF |
| `lowstate` | `/joint_states`, `/battery` |
| `utlidar` cloud | `/scan` |
| `/api/sport/request` | Outbound sport API (not exposed on ROS in M4 scaffold) |

## Safety

- Velocity defaults: **0.5 m/s** forward, **0.3 m/s** lateral, **1.0 rad/s** yaw (spec ceilings 1.5 m/s linear, 2.0 rad/s yaw).
- **`ROS_DOMAIN_ID=0`** is refused unless `OHHO_ARM_HARDWARE=1` and an interactive TTY confirmation phrase is entered (agents and CI fail closed).
- Sim / dev: use **`ROS_DOMAIN_ID=1`** (or any non-zero domain isolated from the robot).

## Sim only, not hardware-tested

This mapping is not validated on a physical Go2. The default node uses `MockSportTransport`.

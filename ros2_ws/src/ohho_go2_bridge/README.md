# ohho_go2_bridge — planned, not built

**Status: planned. Nothing in this package is implemented.**

This ROS 2 package will provide a bridge between the OhhO intelligence layer and
the Unitree Go2 over ROS 2 topics.

## Planned topics

| Topic | Type | Direction |
|---|---|---|
| `/sportmodestate` | `unitree_go/SportModeState` | Subscribe (from robot) |
| `/lowstate` | `unitree_go/LowState` | Subscribe (from robot) |
| `/api/sport/request` | `unitree_api/Request` | Publish (to robot) |
| `/wirelesscontroller` | `unitree_go/WirelessController` | Subscribe |

## Target distribution

**Primary: ROS 2 Humble** (Unitree-tested). Jazzy: best-effort.

Network: static `192.168.123.99/24` on the robot NIC (hardware phase only).

## Dependencies (planned)

- ROS 2 Humble (WSL2 Ubuntu 22.04, OHH-114)
- `unitree_ros2` message packages (`unitree_go`, `unitree_api`)
- colcon build system

**No `package.xml`, no launch files, no colcon code** are committed here yet.

## Implementation schedule

M4 (by early January 2027, OHH-131/132) per ADR 0001 (proposed, PR #3):
https://github.com/ohho-robotics/ohho-quadruped/pull/3

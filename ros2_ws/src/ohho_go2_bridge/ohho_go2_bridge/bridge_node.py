"""
ROS 2 bridge node (scaffolding, mock transport only).

Subscribes to standard OhhO topics and drives a SportTransport: MockSportTransport
unless one is injected (tests). There is no hardware transport and no unitree_ros2
import. Sensor publishers are declared and stay silent; simulated streams for Nav2
come from the sim-only node in ohho_go2_navigation.
"""

from __future__ import annotations

import time

import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from sensor_msgs.msg import BatteryState, JointState, LaserScan
from std_msgs.msg import Empty, String

from ohho_go2_bridge.cmd_vel_bridge import CmdVelBridge
from ohho_go2_bridge.domain_guard import require_safe_ros_domain
from ohho_go2_bridge.mode_allowlist import resolve_mode
from ohho_go2_bridge.transport import (
    MockSportTransport,
    SportTransport,
    resolve_sport_transport,
)
from ohho_go2_bridge.watchdog import CmdVelWatchdog


class Go2BridgeNode(Node):
    def __init__(self, transport: SportTransport | None = None) -> None:
        super().__init__("go2_bridge")
        self.declare_parameter("use_mock_transport", True)
        self.declare_parameter("watchdog_timeout_sec", 0.3)

        use_mock = self.get_parameter("use_mock_transport").get_parameter_value().bool_value
        timeout = self.get_parameter("watchdog_timeout_sec").get_parameter_value().double_value

        self._transport, refused_real = resolve_sport_transport(
            transport,
            use_mock=use_mock,
        )
        if refused_real:
            self.get_logger().error(
                "use_mock_transport is false; this scaffold is sim-only "
                "and stays on MockSportTransport."
            )
        elif transport is None:
            self.get_logger().info("Using MockSportTransport (no Unitree DDS).")

        self._cmd = CmdVelBridge(
            self._transport,
            CmdVelWatchdog(timeout_sec=timeout),
        )
        self._estop_latched = False

        self.create_subscription(Twist, "/cmd_vel", self._on_cmd_vel, 10)
        self.create_subscription(Empty, "/ohho/estop", self._on_estop, 10)
        self.create_subscription(String, "/ohho/mode", self._on_mode, 10)

        # Declared so the topic graph matches the mapping doc. This node does not
        # publish samples; the sim-only sensor node does that in Nav2 launches.
        self._odom_pub = self.create_publisher(Odometry, "/odom", 10)
        self._joint_pub = self.create_publisher(JointState, "/joint_states", 10)
        self._battery_pub = self.create_publisher(BatteryState, "/battery", 10)
        self._scan_pub = self.create_publisher(LaserScan, "/scan", 10)

        period = max(timeout / 3.0, 0.05)
        self.create_timer(period, self._watchdog_timer)

        self.get_logger().info(
            f"ohho_go2_bridge ready: /cmd_vel -> Move + {timeout * 1000:.0f}ms StopMove watchdog"
        )

    def _on_cmd_vel(self, msg: Twist) -> None:
        if self._estop_latched:
            return
        clamped = self._cmd.on_cmd_vel(
            msg.linear.x,
            msg.linear.y,
            msg.angular.z,
            time.monotonic(),
        )
        if clamped:
            self.get_logger().warning("cmd_vel clamped to SafetyGate velocity caps")

    def _watchdog_timer(self) -> None:
        if self._estop_latched:
            return
        if self._cmd.tick_watchdog(time.monotonic()):
            self.get_logger().info("cmd_vel watchdog fired -> StopMove")

    def _on_estop(self, _msg: Empty) -> None:
        self._estop_latched = True
        if isinstance(self._transport, MockSportTransport):
            self._transport.latch_estop()
        else:
            self._transport.stop_move()
        self.get_logger().error("E-stop latched (human release only in full stack)")

    def _on_mode(self, msg: String) -> None:
        if self._estop_latched:
            return
        try:
            sport_cmd = resolve_mode(msg.data)
        except ValueError as exc:
            self.get_logger().error(f"Refused /ohho/mode: {exc}")
            return
        self._transport.invoke_mode(sport_cmd)
        self.get_logger().info(f"Mode {msg.data} -> sport {sport_cmd}")


def main(args: list[str] | None = None) -> None:
    require_safe_ros_domain()
    rclpy.init(args=args)
    node = Go2BridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()

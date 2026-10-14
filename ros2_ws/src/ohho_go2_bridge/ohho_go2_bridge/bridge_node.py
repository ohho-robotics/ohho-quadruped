"""
ROS 2 bridge node (scaffolding).

Subscribes to standard OhhO topics and drives a SportTransport (mock by default).
Does not import unitree_ros2; DDS / Unitree subscriptions are stubbed for M4.
"""

from __future__ import annotations

import math
import time

import rclpy
from geometry_msgs.msg import TransformStamped, Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from sensor_msgs.msg import BatteryState, JointState, LaserScan
from std_msgs.msg import Empty, String
from tf2_ros import TransformBroadcaster

from ohho_go2_bridge.cmd_vel_bridge import CmdVelBridge
from ohho_go2_bridge.domain_guard import require_safe_ros_domain
from ohho_go2_bridge.mode_allowlist import resolve_mode
from ohho_go2_bridge.transport import MockSportTransport, SportTransport
from ohho_go2_bridge.velocity_limits import clamp_twist
from ohho_go2_bridge.watchdog import CmdVelWatchdog

GO2_JOINT_NAMES = [
    "FL_hip_joint",
    "FL_thigh_joint",
    "FL_calf_joint",
    "FR_hip_joint",
    "FR_thigh_joint",
    "FR_calf_joint",
    "RL_hip_joint",
    "RL_thigh_joint",
    "RL_calf_joint",
    "RR_hip_joint",
    "RR_thigh_joint",
    "RR_calf_joint",
]
GO2_STAND_POSITIONS = [0.0, 0.8, -1.5] * 4


class Go2BridgeNode(Node):
    def __init__(self, transport: SportTransport | None = None) -> None:
        super().__init__("go2_bridge")
        self.declare_parameter("use_mock_transport", True)
        self.declare_parameter("watchdog_timeout_sec", 0.3)
        self.declare_parameter("publish_sim_sensors", False)
        self.declare_parameter("sim_sensor_rate_hz", 20.0)

        use_mock = self.get_parameter("use_mock_transport").get_parameter_value().bool_value
        timeout = self.get_parameter("watchdog_timeout_sec").get_parameter_value().double_value
        self._publish_sim_sensors = (
            self.get_parameter("publish_sim_sensors").get_parameter_value().bool_value
        )
        rate_hz = self.get_parameter("sim_sensor_rate_hz").get_parameter_value().double_value

        if transport is not None:
            self._transport = transport
        elif use_mock:
            self._transport = MockSportTransport()
            self.get_logger().info("Using MockSportTransport (no Unitree DDS).")
        else:
            raise NotImplementedError(
                "Real Unitree transport is not wired in this scaffold; "
                "set use_mock_transport:=true or pass a transport in tests."
            )

        self._cmd = CmdVelBridge(
            self._transport,
            CmdVelWatchdog(timeout_sec=timeout),
        )
        self._estop_latched = False

        # Simulation kinematic integration state
        self._pose_x = 0.0
        self._pose_y = 0.0
        self._pose_yaw = 0.0
        self._vx = 0.0
        self._vy = 0.0
        self._vyaw = 0.0
        self._last_sim_tick = time.monotonic()

        self.create_subscription(Twist, "/cmd_vel", self._on_cmd_vel, 10)
        self.create_subscription(Empty, "/ohho/estop", self._on_estop, 10)
        self.create_subscription(String, "/ohho/mode", self._on_mode, 10)

        self._odom_pub = self.create_publisher(Odometry, "/odom", 10)
        self._joint_pub = self.create_publisher(JointState, "/joint_states", 10)
        self._battery_pub = self.create_publisher(BatteryState, "/battery", 10)
        self._scan_pub = self.create_publisher(LaserScan, "/scan", 10)

        period = max(timeout / 3.0, 0.05)
        self.create_timer(period, self._watchdog_timer)

        self._tf_broadcaster = TransformBroadcaster(self) if self._publish_sim_sensors else None
        if self._publish_sim_sensors:
            dt = 1.0 / max(rate_hz, 1.0)
            self.create_timer(dt, self._sim_sensor_timer)
            self.get_logger().info(
                "Publishing simulated sensors (/odom, /scan, /joint_states, TF) at %.1f Hz",
                rate_hz,
            )

        self.get_logger().info(
            "ohho_go2_bridge ready: /cmd_vel -> Move + %.0fms StopMove watchdog",
            timeout * 1000,
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
        # Cache clamped velocities for sim odometry
        cx, cy, cz, _ = clamp_twist(msg.linear.x, msg.linear.y, msg.angular.z)
        self._vx = cx
        self._vy = cy
        self._vyaw = cz

    def _watchdog_timer(self) -> None:
        if self._estop_latched:
            return
        if self._cmd.tick_watchdog(time.monotonic()):
            self._vx = 0.0
            self._vy = 0.0
            self._vyaw = 0.0
            self.get_logger().info("cmd_vel watchdog fired -> StopMove")

    def _on_estop(self, _msg: Empty) -> None:
        self._estop_latched = True
        self._vx = 0.0
        self._vy = 0.0
        self._vyaw = 0.0
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
            self.get_logger().error("Refused /ohho/mode: %s", exc)
            return
        self._transport.invoke_mode(sport_cmd)
        self.get_logger().info("Mode %s -> sport %s", msg.data, sport_cmd)

    def _sim_sensor_timer(self) -> None:
        now = time.monotonic()
        dt = min(max(now - self._last_sim_tick, 0.0), 0.5)
        self._last_sim_tick = now

        # Kinematic integration in robot local frame
        cos_yaw = math.cos(self._pose_yaw)
        sin_yaw = math.sin(self._pose_yaw)
        self._pose_x += (self._vx * cos_yaw - self._vy * sin_yaw) * dt
        self._pose_y += (self._vx * sin_yaw + self._vy * cos_yaw) * dt
        self._pose_yaw += self._vyaw * dt

        stamp = self.get_clock().now().to_msg()
        qz = math.sin(self._pose_yaw / 2.0)
        qw = math.cos(self._pose_yaw / 2.0)

        # 1. Odometry
        odom = Odometry()
        odom.header.stamp = stamp
        odom.header.frame_id = "odom"
        odom.child_frame_id = "base_link"
        odom.pose.pose.position.x = self._pose_x
        odom.pose.pose.position.y = self._pose_y
        odom.pose.pose.position.z = 0.0
        odom.pose.pose.orientation.z = qz
        odom.pose.pose.orientation.w = qw
        odom.twist.twist.linear.x = self._vx
        odom.twist.twist.linear.y = self._vy
        odom.twist.twist.angular.z = self._vyaw
        self._odom_pub.publish(odom)

        # 2. TF: odom -> base_link
        if self._tf_broadcaster is not None:
            t = TransformStamped()
            t.header.stamp = stamp
            t.header.frame_id = "odom"
            t.child_frame_id = "base_link"
            t.transform.translation.x = self._pose_x
            t.transform.translation.y = self._pose_y
            t.transform.translation.z = 0.0
            t.transform.rotation.z = qz
            t.transform.rotation.w = qw
            self._tf_broadcaster.sendTransform(t)

        # 3. Joint states
        joints = JointState()
        joints.header.stamp = stamp
        joints.name = list(GO2_JOINT_NAMES)
        joints.position = list(GO2_STAND_POSITIONS)
        joints.velocity = [0.0] * len(GO2_JOINT_NAMES)
        joints.effort = [0.0] * len(GO2_JOINT_NAMES)
        self._joint_pub.publish(joints)

        # 4. Laser scan (synthetic room perimeter walls)
        scan = LaserScan()
        scan.header.stamp = stamp
        scan.header.frame_id = "radar"
        scan.angle_min = -math.pi
        scan.angle_max = math.pi
        num_readings = 180
        scan.angle_increment = (2.0 * math.pi) / num_readings
        scan.time_increment = 0.0
        scan.scan_time = dt
        scan.range_min = 0.1
        scan.range_max = 20.0
        # Simulated box room (6m x 6m): distance to walls from current pose
        room_half = 3.0
        ranges: list[float] = []
        for i in range(num_readings):
            angle = scan.angle_min + i * scan.angle_increment + self._pose_yaw
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            d = 5.0
            if abs(cos_a) > 1e-3:
                dx = (room_half - self._pose_x if cos_a > 0 else -room_half - self._pose_x) / cos_a
                if dx > 0:
                    d = min(d, dx)
            if abs(sin_a) > 1e-3:
                dy = (room_half - self._pose_y if sin_a > 0 else -room_half - self._pose_y) / sin_a
                if dy > 0:
                    d = min(d, dy)
            ranges.append(max(scan.range_min, min(scan.range_max, d)))
        scan.ranges = ranges
        self._scan_pub.publish(scan)

        # 5. Battery
        battery = BatteryState()
        battery.header.stamp = stamp
        battery.percentage = 0.85
        battery.voltage = 28.8
        battery.present = True
        self._battery_pub.publish(battery)

    def publish_placeholder_sensor_topics(self) -> None:
        """Publish empty sensor outputs so graph checks pass in smoke tests."""
        stamp = self.get_clock().now().to_msg()
        odom = Odometry()
        odom.header.stamp = stamp
        odom.header.frame_id = "odom"
        odom.child_frame_id = "base_link"
        self._odom_pub.publish(odom)

        joints = JointState()
        joints.header.stamp = stamp
        joints.name = list(GO2_JOINT_NAMES)
        joints.position = list(GO2_STAND_POSITIONS)
        self._joint_pub.publish(joints)

        battery = BatteryState()
        battery.header.stamp = stamp
        self._battery_pub.publish(battery)

        scan = LaserScan()
        scan.header.stamp = stamp
        scan.header.frame_id = "radar"
        self._scan_pub.publish(scan)


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

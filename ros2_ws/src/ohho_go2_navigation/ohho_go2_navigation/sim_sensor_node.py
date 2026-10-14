"""Sim-only kinematic sensors for Nav2 headless runs. Not a hardware driver."""

from __future__ import annotations

import time

import rclpy
from geometry_msgs.msg import TransformStamped, Twist
from nav_msgs.msg import Odometry
from ohho_go2_bridge.domain_guard import require_safe_ros_domain
from ohho_go2_bridge.velocity_limits import clamp_twist
from rclpy.node import Node
from sensor_msgs.msg import BatteryState, JointState, LaserScan
from tf2_ros import TransformBroadcaster

from ohho_go2_navigation.sim_kinematics import (
    GO2_JOINT_NAMES,
    GO2_STAND_POSITIONS,
    SCAN_ANGLE_MAX,
    SCAN_ANGLE_MIN,
    SCAN_RANGE_MAX_M,
    SCAN_RANGE_MIN_M,
    SCAN_READINGS,
    SimKinematics,
)


class Go2SimSensorNode(Node):
    """Publish /odom, /scan, /joint_states, /battery, and odom->base_link TF."""

    def __init__(self) -> None:
        super().__init__("go2_sim_sensors")
        self.declare_parameter("sim_sensor_rate_hz", 20.0)
        self.declare_parameter("watchdog_timeout_sec", 0.3)

        rate_hz = self.get_parameter("sim_sensor_rate_hz").get_parameter_value().double_value
        self._timeout_s = (
            self.get_parameter("watchdog_timeout_sec").get_parameter_value().double_value
        )
        self._kin = SimKinematics()

        self.create_subscription(Twist, "/cmd_vel", self._on_cmd_vel, 10)
        self._odom_pub = self.create_publisher(Odometry, "/odom", 10)
        self._joint_pub = self.create_publisher(JointState, "/joint_states", 10)
        self._battery_pub = self.create_publisher(BatteryState, "/battery", 10)
        self._scan_pub = self.create_publisher(LaserScan, "/scan", 10)
        self._tf_broadcaster = TransformBroadcaster(self)

        period = 1.0 / max(rate_hz, 1.0)
        self.create_timer(period, self._on_timer)
        self.get_logger().info(
            f"Sim-only sensors at {rate_hz:.1f} Hz "
            "(/odom, /scan, /joint_states, /battery, TF). Not hardware."
        )

    def _on_cmd_vel(self, msg: Twist) -> None:
        vx, vy, vyaw, _clamped = clamp_twist(msg.linear.x, msg.linear.y, msg.angular.z)
        self._kin.set_body_velocity(vx, vy, vyaw, time.monotonic())

    def _on_timer(self) -> None:
        now = time.monotonic()
        if self._kin.apply_cmd_timeout(now, self._timeout_s):
            self.get_logger().info("sim cmd_vel timeout -> zero velocity")
        dt = self._kin.integrate(now)
        self._publish(dt)

    def _publish(self, dt: float) -> None:
        stamp = self.get_clock().now().to_msg()
        qz, qw = self._kin.yaw_quaternion()

        odom = Odometry()
        odom.header.stamp = stamp
        odom.header.frame_id = "odom"
        odom.child_frame_id = "base_link"
        odom.pose.pose.position.x = self._kin.x
        odom.pose.pose.position.y = self._kin.y
        odom.pose.pose.orientation.z = qz
        odom.pose.pose.orientation.w = qw
        odom.twist.twist.linear.x = self._kin.vx
        odom.twist.twist.linear.y = self._kin.vy
        odom.twist.twist.angular.z = self._kin.vyaw
        self._odom_pub.publish(odom)

        transform = TransformStamped()
        transform.header.stamp = stamp
        transform.header.frame_id = "odom"
        transform.child_frame_id = "base_link"
        transform.transform.translation.x = self._kin.x
        transform.transform.translation.y = self._kin.y
        transform.transform.rotation.z = qz
        transform.transform.rotation.w = qw
        self._tf_broadcaster.sendTransform(transform)

        joints = JointState()
        joints.header.stamp = stamp
        joints.name = list(GO2_JOINT_NAMES)
        joints.position = list(GO2_STAND_POSITIONS)
        joints.velocity = [0.0] * len(GO2_JOINT_NAMES)
        joints.effort = [0.0] * len(GO2_JOINT_NAMES)
        self._joint_pub.publish(joints)

        scan = LaserScan()
        scan.header.stamp = stamp
        scan.header.frame_id = "radar"
        scan.angle_min = SCAN_ANGLE_MIN
        scan.angle_max = SCAN_ANGLE_MAX
        scan.angle_increment = (SCAN_ANGLE_MAX - SCAN_ANGLE_MIN) / SCAN_READINGS
        scan.time_increment = 0.0
        scan.scan_time = dt
        scan.range_min = SCAN_RANGE_MIN_M
        scan.range_max = SCAN_RANGE_MAX_M
        scan.ranges = self._kin.scan_ranges()
        self._scan_pub.publish(scan)

        battery = BatteryState()
        battery.header.stamp = stamp
        battery.percentage = 0.85
        battery.voltage = 28.8
        battery.present = True
        self._battery_pub.publish(battery)


def main(args: list[str] | None = None) -> None:
    require_safe_ros_domain()
    rclpy.init(args=args)
    node = Go2SimSensorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()

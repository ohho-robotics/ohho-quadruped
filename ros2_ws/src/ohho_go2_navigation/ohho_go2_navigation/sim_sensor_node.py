"""Sim-only kinematic sensors for Nav2 headless runs. Not a hardware driver."""

from __future__ import annotations

import time

import rclpy
from builtin_interfaces.msg import Time
from geometry_msgs.msg import TransformStamped, Twist
from nav_msgs.msg import Odometry
from ohho_go2_bridge.domain_guard import require_safe_ros_domain
from ohho_go2_bridge.velocity_limits import clamp_twist
from ohho_go2_bridge.watchdog import require_positive_finite_timeout
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from rosgraph_msgs.msg import Clock as ClockMsg
from sensor_msgs.msg import BatteryState, JointState, LaserScan
from std_msgs.msg import Empty
from tf2_ros import TransformBroadcaster

try:
    # Humble defines ClockType in rclpy.clock. Jazzy re-exports it from there
    # and also provides rclpy.clock_type.
    from rclpy.clock import Clock, ClockType
except ImportError:
    from rclpy.clock import Clock
    from rclpy.clock_type import ClockType

from ohho_go2_navigation.sim_kinematics import (
    GO2_JOINT_NAMES,
    GO2_STAND_POSITIONS,
    SCAN_ANGLE_MAX,
    SCAN_ANGLE_MIN,
    SCAN_RANGE_MAX_M,
    SCAN_RANGE_MIN_M,
    SCAN_READINGS,
    SimKinematics,
    sensor_timer_period_sec,
)

# Matches the /clock subscription inside rcl (best effort, volatile, depth 1).
_CLOCK_QOS = QoSProfile(
    history=HistoryPolicy.KEEP_LAST,
    depth=1,
    reliability=ReliabilityPolicy.BEST_EFFORT,
    durability=DurabilityPolicy.VOLATILE,
)


class Go2SimSensorNode(Node):
    """Publish /odom, /scan, /joint_states, /battery, and odom->base_link TF.

    When ``use_sim_time`` is true, also publish ``/clock`` from a wall-time
    timer so other nodes' ROS-time timers can advance.
    """

    def __init__(self) -> None:
        super().__init__("go2_sim_sensors")
        self.declare_parameter("sim_sensor_rate_hz", 20.0)
        self.declare_parameter("watchdog_timeout_sec", 0.3)

        rate_hz = self.get_parameter("sim_sensor_rate_hz").get_parameter_value().double_value
        period = sensor_timer_period_sec(rate_hz)
        self._timeout_s = require_positive_finite_timeout(
            self.get_parameter("watchdog_timeout_sec").get_parameter_value().double_value
        )
        self._kin = SimKinematics()
        self._wall_clock = Clock(clock_type=ClockType.SYSTEM_TIME)
        self._sim_origin_s = time.monotonic()

        self.create_subscription(Twist, "/cmd_vel", self._on_cmd_vel, 10)
        self.create_subscription(Empty, "/ohho/estop", self._on_estop, 10)
        self._odom_pub = self.create_publisher(Odometry, "/odom", 10)
        self._joint_pub = self.create_publisher(JointState, "/joint_states", 10)
        self._battery_pub = self.create_publisher(BatteryState, "/battery", 10)
        self._scan_pub = self.create_publisher(LaserScan, "/scan", 10)
        self._tf_broadcaster = TransformBroadcaster(self)
        if not self.has_parameter("use_sim_time"):
            # Launch passes this as an override; declare so the override is visible.
            self.declare_parameter("use_sim_time", False)
        self._clock_pub = None
        if bool(self.get_parameter("use_sim_time").get_parameter_value().bool_value):
            self._clock_pub = self.create_publisher(ClockMsg, "/clock", _CLOCK_QOS)
            self._publish_clock()

        # System time, not ROS time: a sim-time timer would never fire until
        # /clock is already advancing.
        self.create_timer(period, self._on_timer, clock=self._wall_clock)
        clock_note = " Publishing /clock." if self._clock_pub is not None else ""
        self.get_logger().info(
            f"Sim-only sensors at {rate_hz:.1f} Hz "
            f"(/odom, /scan, /joint_states, /battery, TF).{clock_note} Not hardware."
        )

    def _on_cmd_vel(self, msg: Twist) -> None:
        if self._kin.estop_latched:
            return
        vx, vy, vyaw, _clamped = clamp_twist(msg.linear.x, msg.linear.y, msg.angular.z)
        self._kin.set_body_velocity(vx, vy, vyaw, time.monotonic())

    def _on_estop(self, _msg: Empty) -> None:
        self._kin.latch_estop()
        self.get_logger().error("E-stop latched; simulated velocity cleared")

    def _on_timer(self) -> None:
        now = time.monotonic()
        if self._kin.apply_cmd_timeout(now, self._timeout_s):
            self.get_logger().info("sim cmd_vel timeout -> zero velocity")
        dt = self._kin.integrate(now)
        self._publish(dt)

    def _sim_time_msg(self) -> Time:
        """Sim time starts at zero and advances with the wall clock."""
        elapsed_ns = int((time.monotonic() - self._sim_origin_s) * 1_000_000_000)
        if elapsed_ns < 0:
            elapsed_ns = 0
        stamp = Time()
        stamp.sec = int(elapsed_ns // 1_000_000_000)
        stamp.nanosec = int(elapsed_ns % 1_000_000_000)
        return stamp

    def _publish_clock(self) -> None:
        if self._clock_pub is None:
            return
        msg = ClockMsg()
        msg.clock = self._sim_time_msg()
        self._clock_pub.publish(msg)

    def _publish(self, dt: float) -> None:
        if self._clock_pub is not None:
            stamp = self._sim_time_msg()
            clock_msg = ClockMsg()
            clock_msg.clock = stamp
            self._clock_pub.publish(clock_msg)
        else:
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

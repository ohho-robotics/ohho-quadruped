"""
Launch robot_state_publisher and RViz for Unitree Go2.

Connects robot_state_publisher to /joint_states (published by ohho_go2_bridge).
"""

from __future__ import annotations

from pathlib import Path

from ament_index_python.packages import PackageNotFoundError, get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def _find_package_dir() -> Path:
    try:
        return Path(get_package_share_directory("go2_description"))
    except (PackageNotFoundError, Exception):
        # Fallback to local workspace checkout
        return Path(__file__).resolve().parents[1]


def generate_launch_description() -> LaunchDescription:
    pkg_dir = _find_package_dir()
    default_urdf = str(pkg_dir / "urdf" / "go2_description.urdf")
    default_rviz = str(pkg_dir / "rviz" / "go2.rviz")

    use_sim_time = LaunchConfiguration("use_sim_time")
    use_bridge_joint_states = LaunchConfiguration("use_bridge_joint_states")
    rviz = LaunchConfiguration("rviz")
    rviz_config = LaunchConfiguration("rviz_config")
    urdf_file = LaunchConfiguration("urdf_file")

    urdf_arg = DeclareLaunchArgument(
        "urdf_file",
        default_value=default_urdf,
        description="Path to go2_description URDF file",
    )
    sim_time_arg = DeclareLaunchArgument(
        "use_sim_time",
        default_value="false",
        description="Use simulation (MuJoCo/clock) time if true",
    )
    bridge_joints_arg = DeclareLaunchArgument(
        "use_bridge_joint_states",
        default_value="true",
        description="Expect /joint_states from ohho_go2_bridge; false for offline JSP",
    )
    rviz_arg = DeclareLaunchArgument(
        "rviz",
        default_value="true",
        description="Launch RViz2 for visualization",
    )
    rviz_config_arg = DeclareLaunchArgument(
        "rviz_config",
        default_value=default_rviz,
        description="Path to RViz configuration file",
    )

    # Use Command substitution so urdf_file can be overridden at runtime
    robot_description = ParameterValue(
        Command(["cat ", urdf_file]),
        value_type=str,
    )

    # robot_state_publisher receives /joint_states from ohho_go2_bridge
    robot_state_pub_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="screen",
        parameters=[
            {
                "robot_description": robot_description,
                "use_sim_time": use_sim_time,
            }
        ],
    )

    # Offline fallback if bridge is not publishing /joint_states
    joint_state_pub_node = Node(
        package="joint_state_publisher",
        executable="joint_state_publisher",
        name="joint_state_publisher",
        output="screen",
        parameters=[{"use_sim_time": use_sim_time}],
        condition=UnlessCondition(use_bridge_joint_states),
    )

    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        arguments=["-d", rviz_config],
        parameters=[{"use_sim_time": use_sim_time}],
        condition=IfCondition(rviz),
    )

    return LaunchDescription(
        [
            urdf_arg,
            sim_time_arg,
            bridge_joints_arg,
            rviz_arg,
            rviz_config_arg,
            robot_state_pub_node,
            joint_state_pub_node,
            rviz_node,
        ]
    )

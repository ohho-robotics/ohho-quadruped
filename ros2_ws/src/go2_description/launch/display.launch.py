"""
Launch robot_state_publisher and RViz for the Go2 description.

Sim only, no gait controller. robot_state_publisher listens on /joint_states.
ohho_go2_bridge declares that topic but does not publish samples. The sim-only
sensor node in ohho_go2_navigation publishes it in Nav2 launches. Set
use_bridge_joint_states:=false for offline joint states, and
use_joint_state_publisher_gui:=true for the slider GUI.
"""

from __future__ import annotations

from pathlib import Path

from ament_index_python.packages import PackageNotFoundError, get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PythonExpression
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
    use_jsp_gui = LaunchConfiguration("use_joint_state_publisher_gui")
    rviz = LaunchConfiguration("rviz")
    rviz_config = LaunchConfiguration("rviz_config")

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
        description=(
            "If true, do not start joint_state_publisher_gui. /joint_states must come "
            "from another node. ohho_go2_bridge does not publish samples; the "
            "sim-only sensor node in ohho_go2_navigation does in Nav2 launches. "
            "Set false for offline joint sliders."
        ),
    )
    jsp_gui_arg = DeclareLaunchArgument(
        "use_joint_state_publisher_gui",
        default_value="false",
        description=(
            "When use_bridge_joint_states is false, launch joint_state_publisher_gui "
            "instead of joint_state_publisher"
        ),
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

    # Read the URDF in Python so a path that contains spaces stays one path.
    # Humble's Command substitution splits an unquoted path on whitespace.
    def _robot_state_publisher(context, *_args, **_kwargs):
        urdf_path = LaunchConfiguration("urdf_file").perform(context)
        robot_description = Path(urdf_path).read_text(encoding="utf-8")
        return [
            Node(
                package="robot_state_publisher",
                executable="robot_state_publisher",
                name="robot_state_publisher",
                output="screen",
                parameters=[
                    {
                        "robot_description": ParameterValue(
                            robot_description, value_type=str
                        ),
                        "use_sim_time": LaunchConfiguration("use_sim_time"),
                    }
                ],
            )
        ]

    # Offline fallback when no other node publishes /joint_states.
    # The GUI publisher is optional and is not started together with the plain one.
    offline_plain = IfCondition(
        PythonExpression(
            [
                "'",
                use_bridge_joint_states,
                "'.lower() == 'false' and '",
                use_jsp_gui,
                "'.lower() == 'false'",
            ]
        )
    )
    offline_gui = IfCondition(
        PythonExpression(
            [
                "'",
                use_bridge_joint_states,
                "'.lower() == 'false' and '",
                use_jsp_gui,
                "'.lower() == 'true'",
            ]
        )
    )
    joint_state_pub_node = Node(
        package="joint_state_publisher",
        executable="joint_state_publisher",
        name="joint_state_publisher",
        output="screen",
        parameters=[{"use_sim_time": use_sim_time}],
        condition=offline_plain,
    )
    joint_state_pub_gui_node = Node(
        package="joint_state_publisher_gui",
        executable="joint_state_publisher_gui",
        name="joint_state_publisher_gui",
        output="screen",
        parameters=[{"use_sim_time": use_sim_time}],
        condition=offline_gui,
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
            jsp_gui_arg,
            rviz_arg,
            rviz_config_arg,
            OpaqueFunction(function=_robot_state_publisher),
            joint_state_pub_node,
            joint_state_pub_gui_node,
            rviz_node,
        ]
    )

"""
All-in-one Go2 simulation, bridge, SLAM, and Nav2 bringup.

Launches:
1. go2_description (robot_state_publisher)
2. ohho_go2_bridge (/cmd_vel sport mock)
3. sim-only kinematic sensors when use_mock_sim:=true (/odom, /scan, /joint_states, TF)
4. slam_toolbox (online async 2D mapping from /scan)
5. Nav2 (planner, controller, smoother, recoveries, BT navigator)
6. RViz2 (when headless:=false)
7. Optional MuJoCo simulation subprocess (when use_mock_sim:=false)
"""

from __future__ import annotations

import os
from pathlib import Path

from ament_index_python.packages import PackageNotFoundError, get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
    SetEnvironmentVariable,
)
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def _find_nav_package_dir() -> Path:
    try:
        return Path(get_package_share_directory("ohho_go2_navigation"))
    except (PackageNotFoundError, Exception):
        return Path(__file__).resolve().parents[1]


def _find_desc_package_dir() -> Path:
    try:
        return Path(get_package_share_directory("go2_description"))
    except (PackageNotFoundError, Exception):
        return Path(__file__).resolve().parents[2] / "go2_description"


def generate_launch_description() -> LaunchDescription:
    nav_pkg = _find_nav_package_dir()
    desc_pkg = _find_desc_package_dir()

    default_nav2_params = str(nav_pkg / "config" / "nav2_params.yaml")
    default_slam_params = str(nav_pkg / "config" / "slam_toolbox_params.yaml")
    default_rviz_config = str(nav_pkg / "config" / "rviz_nav2.rviz")
    default_urdf = str(desc_pkg / "urdf" / "go2_description.urdf")

    use_sim_time = LaunchConfiguration("use_sim_time")
    headless = LaunchConfiguration("headless")
    use_mock_sim = LaunchConfiguration("use_mock_sim")
    scene = LaunchConfiguration("scene")
    nav2_params_file = LaunchConfiguration("nav2_params_file")
    slam_params_file = LaunchConfiguration("slam_params_file")
    rviz_config = LaunchConfiguration("rviz_config")
    autostart = LaunchConfiguration("autostart")

    # Arguments
    sim_time_arg = DeclareLaunchArgument(
        "use_sim_time",
        default_value="true",
        description="Use simulation time if true",
    )
    headless_arg = DeclareLaunchArgument(
        "headless",
        default_value="false",
        description="Run without GUI / RViz2 (ideal for CI and headless containers)",
    )
    mock_sim_arg = DeclareLaunchArgument(
        "use_mock_sim",
        default_value="true",
        description="Use the sim-only kinematic sensor node; set false to launch unitree_mujoco",
    )
    scene_arg = DeclareLaunchArgument(
        "scene",
        default_value="office",
        description="MuJoCo scene description (office, flat, terrain)",
    )
    nav2_params_arg = DeclareLaunchArgument(
        "nav2_params_file",
        default_value=default_nav2_params,
        description="Path to Nav2 params YAML",
    )
    slam_params_arg = DeclareLaunchArgument(
        "slam_params_file",
        default_value=default_slam_params,
        description="Path to slam_toolbox params YAML",
    )
    rviz_config_arg = DeclareLaunchArgument(
        "rviz_config",
        default_value=default_rviz_config,
        description="Path to RViz2 configuration file",
    )
    autostart_arg = DeclareLaunchArgument(
        "autostart",
        default_value="true",
        description="Autostart Nav2 lifecycle stack",
    )

    # Enforce safe ROS domain (domain 1 for sim, never 0)
    domain_env = SetEnvironmentVariable(
        "ROS_DOMAIN_ID",
        os.environ.get("ROS_DOMAIN_ID", "1") or "1",
    )
    localhost_env = SetEnvironmentVariable(
        "ROS_LOCALHOST_ONLY",
        os.environ.get("ROS_LOCALHOST_ONLY", "1") or "1",
    )

    # 1. Robot description (robot_state_publisher)
    urdf_content = ""
    if Path(default_urdf).exists():
        urdf_content = Path(default_urdf).read_text(encoding="utf-8")

    rsp_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="screen",
        parameters=[
            {
                "robot_description": ParameterValue(urdf_content, value_type=str),
                "use_sim_time": use_sim_time,
            }
        ],
    )

    # 2. Bridge node
    bridge_node = Node(
        package="ohho_go2_bridge",
        executable="go2_bridge_node",
        name="go2_bridge",
        output="screen",
        parameters=[
            {
                "use_mock_transport": True,
                "watchdog_timeout_sec": 0.3,
                "use_sim_time": ParameterValue(use_sim_time, value_type=bool),
            }
        ],
    )

    # Sim-only kinematic sensors. Not launched on the MuJoCo path.
    sim_sensor_node = Node(
        package="ohho_go2_navigation",
        executable="go2_sim_sensor_node",
        name="go2_sim_sensors",
        output="screen",
        parameters=[
            {
                "sim_sensor_rate_hz": 20.0,
                "watchdog_timeout_sec": 0.3,
                "use_sim_time": ParameterValue(use_sim_time, value_type=bool),
            }
        ],
        condition=IfCondition(use_mock_sim),
    )

    # 3. slam_toolbox (online async)
    slam_node = Node(
        package="slam_toolbox",
        executable="async_slam_toolbox_node",
        name="slam_toolbox",
        output="screen",
        parameters=[
            slam_params_file,
            {"use_sim_time": ParameterValue(use_sim_time, value_type=bool)},
        ],
    )

    # 4. Nav2 stack
    nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(str(nav_pkg / "launch" / "nav2.launch.py")),
        launch_arguments={
            "use_sim_time": use_sim_time,
            "params_file": nav2_params_file,
            "autostart": autostart,
        }.items(),
    )

    # 5. RViz2 (GUI only)
    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        arguments=["-d", rviz_config],
        parameters=[{"use_sim_time": use_sim_time}],
        condition=UnlessCondition(headless),
    )

    # 6. Optional MuJoCo simulation process (when use_mock_sim is false)
    mujoco_sim_proc = ExecuteProcess(
        cmd=["python3", "sim/run_go2.py", "--scene", scene, "--headless"],
        output="screen",
        condition=UnlessCondition(use_mock_sim),
    )

    return LaunchDescription(
        [
            domain_env,
            localhost_env,
            sim_time_arg,
            headless_arg,
            mock_sim_arg,
            scene_arg,
            nav2_params_arg,
            slam_params_arg,
            rviz_config_arg,
            autostart_arg,
            rsp_node,
            bridge_node,
            sim_sensor_node,
            slam_node,
            nav2_launch,
            rviz_node,
            mujoco_sim_proc,
        ]
    )

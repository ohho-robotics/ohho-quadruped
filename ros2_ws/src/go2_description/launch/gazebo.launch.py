"""Spawn the Go2 URDF in Gazebo Harmonic.

Sim only, no gait controller. ROS 2 Jazzy starts gz sim (Harmonic, gz-sim 8)
and ros_gz_sim create. The model is a static visual, standing or lying.
The vendored xacro/gazebo.xacro classic plugins are not loaded.
"""

from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path

from ament_index_python.packages import PackageNotFoundError, get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, LogInfo, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def _load_spawn_pose():
    path = Path(__file__).resolve().parent / "spawn_pose.py"
    spec = importlib.util.spec_from_file_location("go2_spawn_pose", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _package_dir() -> Path:
    try:
        return Path(get_package_share_directory("go2_description"))
    except (PackageNotFoundError, Exception):
        return Path(__file__).resolve().parents[1]


def _empty_world() -> str:
    roots = (
        Path("/opt/ros/jazzy/opt/gz_sim_vendor/share/gz"),
        Path("/opt/ros/humble/opt/gz_sim_vendor/share/gz"),
        Path("/usr/share/gz"),
    )
    for root in roots:
        found = sorted(root.glob("gz-sim*/worlds/empty.sdf"))
        if found:
            return str(found[-1])
    return "empty.sdf"


def _launch_setup(context, *_args, **_kwargs):
    spawn_pose = _load_spawn_pose()
    pose = LaunchConfiguration("pose").perform(context).strip().lower()
    gui = LaunchConfiguration("gui").perform(context).strip().lower()
    use_sim_time = LaunchConfiguration("use_sim_time")
    entity = LaunchConfiguration("entity_name").perform(context).strip()
    urdf_path = Path(LaunchConfiguration("urdf_file").perform(context))
    package_root = _package_dir()
    spec = spawn_pose.build_spawn(
        urdf_path.read_text(encoding="utf-8"),
        pose,
        package_root=package_root,
    )
    spawn_file = Path(tempfile.gettempdir()) / f"ohh_go2_{pose}_spawn.urdf"
    spawn_file.write_text(spec.urdf, encoding="utf-8")

    world = _empty_world()
    gz_args = f"-r -v 1 {world}"
    if gui == "false":
        gz_args = f"-r -s -v 1 {world}"

    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [FindPackageShare("ros_gz_sim"), "launch", "gz_sim.launch.py"]
            )
        ),
        launch_arguments={"gz_args": gz_args}.items(),
    )
    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="screen",
        parameters=[
            {
                "robot_description": spec.urdf,
                "use_sim_time": use_sim_time,
            }
        ],
    )
    clock_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        name="clock_bridge",
        arguments=["/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock"],
        output="screen",
    )
    create = Node(
        package="ros_gz_sim",
        executable="create",
        name="spawn_go2",
        output="screen",
        arguments=[
            "-world",
            "empty",
            "-file",
            str(spawn_file),
            "-name",
            entity,
            "-x",
            f"{spec.x:.6f}",
            "-y",
            f"{spec.y:.6f}",
            "-z",
            f"{spec.z:.6f}",
            "-R",
            f"{spec.roll:.6f}",
            "-P",
            f"{spec.pitch:.6f}",
            "-Y",
            f"{spec.yaw:.6f}",
        ],
    )
    summary = (
        f"go2 visual spawn pose={pose} "
        f"xyz=({spec.x:.3f},{spec.y:.3f},{spec.z:.3f}) "
        f"rpy=({spec.roll:.3f},{spec.pitch:.3f},{spec.yaw:.3f}) "
        "static, no gait controller"
    )
    return [LogInfo(msg=summary), gz_sim, clock_bridge, robot_state_publisher, create]


def generate_launch_description() -> LaunchDescription:
    pkg_dir = _package_dir()
    default_urdf = str(pkg_dir / "urdf" / "go2_description.urdf")
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "pose",
                default_value="standing",
                description="Visual spawn pose: standing or lying. No gait controller.",
            ),
            DeclareLaunchArgument(
                "urdf_file",
                default_value=default_urdf,
                description="Source URDF. Leg joints are baked into the chosen pose at spawn.",
            ),
            DeclareLaunchArgument(
                "use_sim_time",
                default_value="true",
                description="Use the Gazebo /clock time.",
            ),
            DeclareLaunchArgument(
                "gui",
                default_value="true",
                description="Start the Gazebo GUI. false adds gz sim -s (server only).",
            ),
            DeclareLaunchArgument(
                "entity_name",
                default_value="go2",
                description="Name of the spawned Gazebo entity.",
            ),
            OpaqueFunction(function=_launch_setup),
        ]
    )

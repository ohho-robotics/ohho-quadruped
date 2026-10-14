import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    share = get_package_share_directory("ohho_go2_bridge")
    config = os.path.join(share, "config", "bridge.yaml")
    return LaunchDescription(
        [
            Node(
                package="ohho_go2_bridge",
                executable="go2_bridge_node",
                name="go2_bridge",
                output="screen",
                parameters=[config],
            ),
        ]
    )

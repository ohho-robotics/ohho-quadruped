from setuptools import find_packages, setup

package_name = "ohho_go2_bridge"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", ["launch/bridge.launch.py"]),
        ("share/" + package_name + "/config", ["config/bridge.yaml"]),
        ("share/" + package_name + "/docs", ["docs/TOPIC_MAPPING.md"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="OhhO Robotics",
    maintainer_email="dev@ohho-robotics.com",
    description="OhhO ROS 2 bridge scaffolding for Unitree Go2 (sport-mode).",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "go2_bridge_node = ohho_go2_bridge.bridge_node:main",
        ],
    },
)

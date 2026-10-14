from setuptools import find_packages, setup

package_name = "ohho_go2_navigation"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        (
            "share/" + package_name + "/launch",
            [
                "launch/go2_nav_sim.launch.py",
                "launch/nav2.launch.py",
                "launch/slam.launch.py",
            ],
        ),
        (
            "share/" + package_name + "/config",
            [
                "config/nav2_params.yaml",
                "config/slam_toolbox_params.yaml",
                "config/rviz_nav2.rviz",
            ],
        ),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="OhhO Robotics",
    maintainer_email="dev@ohho-robotics.com",
    description="Nav2 configuration, SLAM toolbox setup, and all-in-one sim launch for Go2.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "go2_sim_sensor_node = ohho_go2_navigation.sim_sensor_node:main",
        ],
    },
)

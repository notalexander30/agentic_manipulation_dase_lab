"""Reuse the full IFRA setup while exposing named teaching stages."""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def launch_stage(stage):
    package = get_package_share_directory('block_skills')
    return LaunchDescription([
        DeclareLaunchArgument('config', default_value=os.path.join(package, 'config', 'blocks.json')),
        DeclareLaunchArgument('gui', default_value='true'),
        DeclareLaunchArgument('rviz', default_value='true'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(package, 'launch', 'sim.launch.py')),
            launch_arguments={
                'stage': stage, 'config': LaunchConfiguration('config'),
                'gui': LaunchConfiguration('gui'), 'rviz': LaunchConfiguration('rviz'),
            }.items()),
    ])

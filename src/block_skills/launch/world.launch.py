"""Open Gazebo with the table and ROS plugins, before loading a robot."""
from block_skills.launch_stage import launch_stage


def generate_launch_description():
    return launch_stage('world')

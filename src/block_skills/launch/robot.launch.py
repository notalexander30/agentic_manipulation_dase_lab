"""Load the UR10e, controllers, MoveIt and RViz into an existing world."""
from block_skills.launch_stage import launch_stage


def generate_launch_description():
    return launch_stage('robot')

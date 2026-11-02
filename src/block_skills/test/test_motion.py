"""Distinguish rejected plans from execution failures before retrying."""
from types import SimpleNamespace
import pytest

pytest.importorskip('rclpy')
pytest.importorskip('block_interfaces.action')
from action_msgs.msg import GoalStatus
from moveit_msgs.msg import MoveItErrorCodes
from block_skills.server import Server, SkillError


@pytest.mark.parametrize('error, expected', [
    (MoveItErrorCodes.INVALID_MOTION_PLAN, 'PLANNING_FAILED'),
    (MoveItErrorCodes.CONTROL_FAILED, 'MOTION_FAILED'),
])
def test_generated_trajectory_rejection_is_not_controller_failure(error, expected):
    response = SimpleNamespace(status=GoalStatus.STATUS_ABORTED, result=SimpleNamespace(
        error_code=SimpleNamespace(val=error), planned_trajectory=SimpleNamespace(
            joint_trajectory=SimpleNamespace(points=[object()]))))
    handle = SimpleNamespace(accepted=True, get_result_async=lambda: response)
    client = SimpleNamespace(wait_for_server=lambda **_: True, send_goal_async=lambda _: handle)
    fake = SimpleNamespace(motion_timeout=240, check_cancel=lambda: None,
                           wait=lambda future, **_: future)
    with pytest.raises(SkillError) as exc:
        Server.run_action(fake, client, object())
    assert exc.value.code == expected

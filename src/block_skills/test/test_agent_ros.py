"""Exercise the real ROS mapping without requiring generated ROS packages."""
import importlib.util
from pathlib import Path
import sys
import threading
from concurrent.futures import Future
from types import ModuleType, SimpleNamespace as NS
import unittest
from unittest.mock import MagicMock, patch


def goal(**kwargs):
    return NS(**kwargs, target=NS(header=NS(frame_id=''), pose=NS(position=NS(), orientation=NS())))


class RosMappingTests(unittest.TestCase):
    def setUp(self):
        modules = {}
        for name in ('rclpy', 'rclpy.node', 'rclpy.action', 'rclpy.executors',
                     'rosidl_runtime_py', 'rosidl_runtime_py.convert', 'block_interfaces',
                     'block_interfaces.action', 'block_interfaces.srv', 'std_srvs', 'std_srvs.srv'):
            modules[name] = ModuleType(name)
        modules['rclpy.node'].Node = MagicMock()
        modules['rclpy.action'].ActionClient = MagicMock()
        modules['rclpy.executors'].SingleThreadedExecutor = MagicMock()
        modules['rosidl_runtime_py.convert'].message_to_ordereddict = lambda x: vars(x)
        modules['block_interfaces.action'].PickPlace = NS(Goal=goal)
        modules['block_interfaces.srv'].Blocks = NS(Request=lambda **kw: NS(**kw))
        modules['std_srvs.srv'].Trigger = NS(Request=lambda: NS())
        self.patcher = patch.dict(sys.modules, modules)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        path = Path(__file__).parents[1]/'block_skills/agent_ros.py'
        spec = importlib.util.spec_from_file_location('block_skills._test_agent_ros', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.backend = module.RosBackend.__new__(module.RosBackend)
        self.real_wait = module.RosBackend.wait.__get__(self.backend)
        self.backend.action_client = MagicMock()
        self.backend.node = MagicMock()
        self.result = NS(success=True, verified=True, holding_block=False, code='OK', task_id='a'*32,
                         final_pose={'frame':'world'}, evidence_files=[], report_file='/work/artifacts/result.json',
                         already_complete=False, message='verified')
        self.handle = MagicMock(accepted=True)
        self.backend.wait = MagicMock(side_effect=[self.handle, NS(status=4, result=self.result)])

    def test_stack_goal_and_result_fields(self):
        result = self.backend.action(dict(block='blue_block', support='red_block', evidence='none'))
        sent = self.backend.action_client.send_goal_async.call_args.args[0]
        self.assertEqual((sent.block, sent.support_block, sent.evidence), ('blue_block', 'red_block', 'none'))
        self.assertEqual(result, dict(vars(self.result), action_status=4))
        self.handle.get_result_async.assert_called_once()

    def test_world_pose_yaw_mapping(self):
        self.backend.action(dict(block='blue_block', evidence='none', target_pose=dict(x=.8, y=-.2, z=.675, yaw=0)))
        sent = self.backend.action_client.send_goal_async.call_args.args[0]
        self.assertEqual(sent.target.header.frame_id, 'world')
        self.assertEqual(vars(sent.target.pose.position), dict(x=.8, y=-.2, z=.675))
        self.assertEqual(vars(sent.target.pose.orientation), dict(z=0., w=1.))

    def test_rejection_never_waits_for_result(self):
        from block_skills.agent import AgentError
        self.handle.accepted = False
        with self.assertRaises(AgentError) as caught:
            self.backend.action(dict(block='blue_block', support='red_block', evidence='none'))
        self.assertEqual(caught.exception.code, 'GOAL_REJECTED')
        self.handle.get_result_async.assert_not_called()

    def test_canceled_envelope_preserves_error(self):
        self.result.success, self.result.code = False, 'CANCELED'
        self.backend.wait.side_effect = [self.handle, NS(status=5, result=self.result)]
        result = self.backend.action(dict(block='blue_block', support='red_block', evidence='none'))
        self.assertFalse(result['success'])
        self.assertEqual(result['code'], 'CANCELED')
        self.assertEqual(result['action_status'], 5)

    def test_timeout_cancels_without_replaying(self):
        self.backend.wait.side_effect = [self.handle, TimeoutError('result missing')]
        with self.assertRaises(TimeoutError):
            self.backend.action(dict(block='blue_block', support='red_block', evidence='none'))
        self.handle.cancel_goal_async.assert_called_once()
        self.backend.action_client.send_goal_async.assert_called_once()

    def test_cancel_while_goal_acceptance_pending_waits_for_terminal_result(self):
        self.backend.wait = self.real_wait
        accepted, result_future = Future(), Future()
        submitted, cancel_seen = threading.Event(), threading.Event()
        cancel_event = threading.Event()
        def submit(*args, **kwargs):
            submitted.set()
            return accepted
        self.backend.action_client.send_goal_async.side_effect = submit
        self.handle.get_result_async.return_value = result_future
        self.handle.cancel_goal_async.side_effect = lambda: cancel_seen.set()
        results = []
        thread = threading.Thread(target=lambda: results.append(self.backend.action(
            dict(block='blue_block', support='red_block', evidence='none'), cancel_event)))
        thread.start()
        try:
            self.assertTrue(submitted.wait(2))
            cancel_event.set()
            accepted.set_result(self.handle)
            self.assertTrue(cancel_seen.wait(2))
            self.assertTrue(thread.is_alive(), 'Cancellation request must not replace the final result.')
            self.assertEqual(self.handle.cancel_goal_async.call_count, 1)
        finally:
            if not accepted.done():
                accepted.set_result(self.handle)
            self.result.success, self.result.code = False, 'CANCELED'
            result_future.set_result(NS(status=5, result=self.result))
            thread.join(3)
        self.assertEqual(results[0]['code'], 'CANCELED')
        self.backend.action_client.send_goal_async.assert_called_once()

    def test_cancel_during_discovery_prevents_submission(self):
        from block_skills.agent import AgentError
        event = threading.Event()
        def available(**kwargs):
            event.set()
            return True
        self.backend.action_client.wait_for_server.side_effect = available
        with self.assertRaises(AgentError) as caught:
            self.backend.action(dict(block='blue_block', support='red_block', evidence='none'), event)
        self.assertEqual(caught.exception.code, 'CANCELED')
        self.backend.action_client.send_goal_async.assert_not_called()


if __name__ == '__main__':
    unittest.main()

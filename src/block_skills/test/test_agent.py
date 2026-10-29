"""Policy and real HTTP/client tests with a mocked ROS transport."""
import importlib.util
import itertools
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib import request, error

from block_skills.agent import Agent, AgentError
from block_skills.agent_http import make_server
from block_skills.geometry import load_config


class Backend:
    def __init__(self):
        self.goals = []
        self.result = dict(success=True, verified=True, holding_block=False,
                           code='OK', task_id='a'*32, already_complete=False,
                           evidence_files=[], report_file='result.json')
        config = load_config(Path(__file__).parents[1]/'config/blocks.json')
        self.inventory = [dict(name=b['name'], color=b['color'], pose=dict(pose=dict(
            position=dict(zip(('x', 'y', 'z'), b['position'])),
            orientation=dict(x=0., y=0., z=0., w=1.)))) for b in config['blocks']]

    def status(self):
        return dict(success=True, message='ready=True; busy=False; holding=none; fault=none')

    def blocks(self):
        return self.inventory

    def action(self, goal, cancel_event=None):
        self.goals.append(goal)
        return dict(self.result)

    def add(self, args):
        return dict(success=True, message='spawn_random complete', blocks=self.inventory)


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.backend = Backend()
        self.agent = Agent(self.backend, self.tmp.name,
                           config=load_config(Path(__file__).parents[1]/'config/blocks.json'))

    def test_all_permutations(self):
        for order in itertools.permutations(('red', 'green', 'blue')):
            self.backend.goals.clear()
            result = self.agent.invoke('stack_order', dict(order=list(order)))
            self.assertTrue(result['completed'])
            self.assertEqual([(g['block'], g['support']) for g in self.backend.goals],
                             [(order[1]+'_block', order[0]+'_block'), (order[2]+'_block', order[1]+'_block')])

    def test_failure_stops_order_preserves_codes(self):
        for code in ('BLOCK_NOT_TOP', 'STACK_LIMIT', 'PLANNING_FAILED', 'MOTION_FAILED', 'CANCELED'):
            self.backend.goals.clear()
            self.backend.result.update(success=False, code=code)
            result = self.agent.invoke('stack_order', dict(order='RGB'))
            self.assertFalse(result['completed'])
            self.assertEqual(result['steps'][0]['code'], code)
            self.assertEqual(len(self.backend.goals), 1)

    def test_acceptance_is_not_completion(self):
        self.backend.result['verified'] = False
        result = self.agent.invoke('stack', dict(block='blue', support='red'))
        self.assertFalse(result['completed'])
        self.assertTrue(result['success'])  # Original transport result is retained.

    def test_second_step_failure_returns_partial_results(self):
        original = self.backend.action
        def action(goal, cancel_event=None):
            result = original(goal)
            if len(self.backend.goals) == 2:
                result.update(success=False, code='TRACKING_FAILED')
            return result
        self.backend.action = action
        result = self.agent.invoke('stack_order', dict(order='BGR'))
        self.assertFalse(result['completed'])
        self.assertTrue(result['steps'][0]['completed'])
        self.assertEqual(result['steps'][1]['code'], 'TRACKING_FAILED')
        self.backend.goals.clear()
        def rejected(goal, cancel_event=None):
            if self.backend.goals:
                raise AgentError('GOAL_REJECTED', 'Server became unavailable.')
            return original(goal)
        self.backend.action = rejected
        result = self.agent.invoke('stack_order', dict(order='RGB'))
        self.assertTrue(result['steps'][0]['completed'])
        self.assertFalse(result['completed'])
        self.assertEqual(result['steps'][1]['code'], 'GOAL_REJECTED')

    def test_unready_server_blocks_submission(self):
        self.backend.status = lambda: dict(success=False, message='ready=False; busy=False; holding=none; fault=none')
        with self.assertRaises(AgentError) as caught:
            self.agent.invoke('stack', dict(block='blue', support='red'))
        self.assertEqual(caught.exception.code, 'NOT_READY')
        self.assertEqual(self.backend.goals, [])

    def test_evidence_and_idempotency(self):
        self.backend.result['already_complete'] = True
        self.assertTrue(self.agent.invoke('stack', dict(block='blue', support='red'))['completed'])
        args = dict(block='blue', support='red', evidence='screenshot')
        self.assertFalse(self.agent.invoke('stack', args)['completed'])
        evidence = Path(self.tmp.name)/'scene.png'
        evidence.write_bytes(b'test')
        self.backend.result['evidence_files'] = [str(evidence)]
        self.assertTrue(self.agent.invoke('stack', args)['completed'])
        evidence.unlink()
        self.assertFalse(self.agent.invoke('stack', args)['completed'])

    def test_held_fault_blocks_next_task(self):
        self.backend.result['holding_block'] = True
        self.assertFalse(self.agent.invoke('stack', dict(block='blue', support='red'))['completed'])
        with self.assertRaises(AgentError) as caught:
            self.agent.invoke('add_block', dict(color='yellow'))
        self.assertEqual(caught.exception.code, 'RECOVERY_REQUIRED')

    def test_timeout_latches_uncertainty(self):
        def timeout(goal, cancel_event=None):
            raise TimeoutError('lost result')
        self.backend.action = timeout
        with self.assertRaises(AgentError) as caught:
            self.agent.invoke('stack', dict(block='blue', support='red'))
        self.assertEqual(caught.exception.code, 'EXECUTION_UNKNOWN')
        with self.assertRaises(AgentError) as caught:
            self.agent.invoke('stack', dict(block='blue', support='red'))
        self.assertEqual(caught.exception.code, 'RECOVERY_REQUIRED')

    def test_concurrent_requests_rejected_for_whole_order(self):
        entered, release = threading.Event(), threading.Event()
        original = self.backend.action
        def blocking(goal, cancel_event=None):
            entered.set()
            release.wait(5)
            return original(goal)
        self.backend.action = blocking
        output = []
        thread = threading.Thread(target=lambda: output.append(self.agent.invoke('stack_order', dict(order='RGB'))))
        thread.start()
        try:
            self.assertTrue(entered.wait(2))
            self.assertTrue(self.agent.invoke('get_status', {})['adapter_busy'])
            for op, args in [('stack', dict(block='blue', support='red')), ('add_block', dict(color='yellow'))]:
                with self.assertRaises(AgentError) as caught:
                    self.agent.invoke(op, args)
                self.assertEqual(caught.exception.code, 'BUSY')
        finally:
            release.set()
            thread.join(5)
        self.assertTrue(output[0]['completed'])

    def test_validation_before_motion(self):
        cases = [('stack_order', dict(order='RRG')), ('stack_order', dict(order=[[], 'red', 'blue'])),
                 ('stack', dict(block='missing', support='red')),
                 ('stack', dict(block='red', support='red')), ('stack', dict(block='blue', support='red', raw=True)),
                 ('move_joints', {}), ('pick_place', dict(block='red', target_pose=dict(x=float('nan'), y=0, z=0, yaw=0))),
                 ('add_block', dict(color='purple')), ('add_block', dict(color='red', seed=True)),
                 ('read_result', dict(task_id='../secret'))]
        for op, args in cases:
            with self.subTest(op=op, args=args), self.assertRaises(AgentError):
                self.agent.invoke(op, args)
        self.assertEqual(self.backend.goals, [])
        self.backend.inventory.append(dict(name='red_extra', color='red'))
        with self.assertRaises(AgentError) as caught:
            self.agent.invoke('stack', dict(block='red', support='blue'))
        self.assertEqual(caught.exception.code, 'AMBIGUOUS_BLOCK')
        self.agent.invoke('stack', dict(block='red_block', support='blue'))

    def test_result_read(self):
        folder = Path(self.tmp.name)/('b'*32)
        folder.mkdir()
        (folder/'result.json').write_text(json.dumps(self.backend.result))
        self.assertEqual(self.agent.invoke('read_result', dict(task_id='b'*32)), self.backend.result)

    def test_http_client_roundtrip(self):
        root = Path(__file__).resolve().parents[3]
        path = root/'openclaw-workspace/skills/ur10e-sim/scripts/ur10e_sim.py'
        spec = importlib.util.spec_from_file_location('client', path)
        client = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(client)
        server = make_server(self.agent, ('127.0.0.1', 0), 'test-token')
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f'http://127.0.0.1:{server.server_port}'
        try:
            result = client.invoke('stack_order', dict(order='GBR'), url, 'test-token')
            self.assertTrue(result['completed'], result)
            self.assertEqual(self.backend.goals[0]['support'], 'green_block')
            self.assertEqual(self.backend.goals[1]['block'], 'red_block')
            self.assertEqual(client.invoke('get_status', {}, url, 'wrong')['code'], 'UNAUTHORIZED')
            self.assertEqual(client.invoke('stack', dict(block='unknown', support='red'), url, 'test-token')['code'], 'UNKNOWN_BLOCK')
            self.backend.result.update(success=False, code='PLANNING_FAILED')
            self.assertEqual(client.invoke('stack', dict(block='blue', support='red'), url, 'test-token')['code'], 'PLANNING_FAILED')
            req = request.Request(url+'/code/sdk', headers={'Authorization': 'Bearer test-token'})
            with request.urlopen(req) as response:
                self.assertIn('stack_order', json.load(response)['operations'])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(2)

    def test_http_cancel_bypasses_busy_lock(self):
        path = Path(__file__).resolve().parents[3]/'openclaw-workspace/skills/ur10e-sim/scripts/ur10e_sim.py'
        spec = importlib.util.spec_from_file_location('cancel_client', path)
        client = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(client)
        entered, event_holder, output = threading.Event(), [], []
        def active(goal, cancel_event=None):
            self.backend.goals.append(goal)
            event_holder.append(cancel_event)
            entered.set()
            if not cancel_event.wait(3):
                raise AssertionError('Cancel tool did not reach the active request')
            return dict(self.backend.result, success=False, verified=False, code='CANCELED')
        self.backend.action = active
        server = make_server(self.agent, ('127.0.0.1', 0), 'test-token')
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        url = f'http://127.0.0.1:{server.server_port}'
        execute = threading.Thread(target=lambda: output.append(client.invoke('stack_order', dict(order='RGB'), url, 'test-token')))
        execute.start()
        try:
            self.assertTrue(entered.wait(2))
            status = client.invoke('get_status', {}, url, 'test-token')
            self.assertTrue(status['adapter_busy'])
            payload = dict(request_id=status['active_request_id'])
            self.assertEqual(client.invoke('cancel', payload, url, 'wrong')['code'], 'UNAUTHORIZED')
            self.assertFalse(event_holder[0].is_set())
            result = client.invoke('cancel', payload, url, 'test-token')
            self.assertTrue(result['cancel_requested'])
            self.assertFalse(result['execution_stopped'])
            execute.join(3)
            self.assertEqual(output[0]['code'], 'CANCELED')
            self.assertEqual(len(self.backend.goals), 1)
        finally:
            if event_holder:
                event_holder[0].set()
            execute.join(4)
            server.shutdown()
            server.server_close()
            server_thread.join(2)


if __name__ == '__main__':
    unittest.main()

"""Stateful skill double: exercise tower transitions and cancellation invariants."""
import copy
import itertools
import math
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from block_skills.agent import Agent, AgentError
from block_skills.geometry import load_config, support_chain, check_spacing, yaw_quat
from test_agent import Backend


class SceneBackend(Backend):
    def tower(self, order, base=(.55, -.28, .675)):
        for level, color in enumerate(order):
            self.set_position(color+'_block', [base[0], base[1], base[2]+.05*level])

    def set_position(self, name, xyz, yaw=0):
        block = next(b for b in self.inventory if b['name'] == name)
        block['pose']['pose'] = dict(position=dict(zip(('x', 'y', 'z'), xyz)),
                                    orientation=dict(zip(('x', 'y', 'z', 'w'), yaw_quat(yaw))))

    def positions(self):
        return {b['name']: [b['pose']['pose']['position'][axis] for axis in ('x', 'y', 'z')]
                for b in self.inventory}

    def action(self, goal, cancel_event=None):
        self.goals.append(copy.deepcopy(goal))
        if cancel_event is not None and cancel_event.is_set():
            return dict(self.result, success=False, verified=False, code='CANCELED')
        config = load_config(Path(__file__).parents[1]/'config/blocks.json')
        positions = self.positions()
        name = goal['block']
        if 'support' in goal:
            support = goal['support']
            references = support_chain(config, support, positions)
            target = positions[support][:2]+[positions[support][2]+config['block_size']]
        else:
            references = []
            target = [goal['target_pose'][k] for k in ('x', 'y', 'z')]
        already = math.dist(positions[name], target) < .005
        if not already:
            # Fail loudly if the planner ever tries to pick a supporting block.
            for other in positions:
                if name in support_chain(config, other, positions)[1:]:
                    raise AssertionError(f'Unsafe plan: {other} is above {name}')
            check_spacing(config, target, [p for n, p in positions.items() if n != name and n not in references])
            self.set_position(name, target, goal.get('target_pose', {}).get('yaw', 0))
        return dict(self.result, already_complete=already)


class RearrangeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.config = load_config(Path(__file__).parents[1]/'config/blocks.json')

    def agent(self, backend):
        return Agent(backend, self.tmp.name, config=self.config)

    def test_all_36_tower_transitions(self):
        orders = list(itertools.permutations(('red', 'green', 'blue')))
        for source in orders:
            for target in orders:
                with self.subTest(source=source, target=target):
                    backend = SceneBackend()
                    backend.tower(source)
                    result = self.agent(backend).invoke('stack_order', dict(order=list(target)))
                    self.assertTrue(result['completed'], result)
                    self.assertEqual(support_chain(self.config, target[-1]+'_block', backend.positions()),
                                     [c+'_block' for c in reversed(target)])
                    if source == target:
                        self.assertEqual(len(backend.goals), 2)
                        self.assertTrue(all(s['already_complete'] for s in result['steps']))
                    else:
                        dismantled = [g['block'] for g in backend.goals if 'target_pose' in g]
                        self.assertEqual(dismantled[0], source[-1]+'_block')

    def test_correct_partial_stack_is_preserved(self):
        backend = SceneBackend()
        backend.set_position('green_block', [.55, -.28, .725])
        result = self.agent(backend).invoke('stack_order', dict(order='RGB'))
        self.assertTrue(result['completed'])
        self.assertEqual(len(backend.goals), 2)
        self.assertTrue(result['steps'][0]['already_complete'])

    def test_all_orders_from_each_configured_tower_site(self):
        for base in [b['position'] for b in self.config['blocks']]:
            for source in itertools.permutations(('red', 'green', 'blue')):
                for target in itertools.permutations(('red', 'green', 'blue')):
                    with self.subTest(base=base, source=source, target=target):
                        backend = SceneBackend()
                        backend.tower(source, base)
                        result = self.agent(backend).invoke('stack_order', dict(order=list(target)))
                        self.assertTrue(result['completed'], result)
                        self.assertEqual(support_chain(self.config, target[-1]+'_block', backend.positions()),
                                         [c+'_block' for c in reversed(target)])

    def test_repeated_rearrangements_do_not_drift_to_random_positions(self):
        backend = SceneBackend()
        agent = self.agent(backend)
        sites = [b['position'] for b in self.config['blocks']]
        for order in ['GRB', 'RGB', 'BGR', 'RBG', 'GRB', 'GBR', 'BRG']*3:
            self.assertTrue(agent.invoke('stack_order', dict(order=order))['completed'])
            self.assertTrue(all(any(p[:2] == site[:2] for site in sites) for p in backend.positions().values()))
        for goal in backend.goals:
            if 'target_pose' in goal:
                self.assertIn([goal['target_pose'][axis] for axis in ('x', 'y', 'z')], sites)

    def test_occupied_sites_fail_before_motion_without_random_fallback(self):
        backend = SceneBackend()
        backend.tower(('red', 'green', 'blue'))
        extra = copy.deepcopy(backend.inventory[0])
        extra.update(name='yellow_block', color='yellow')
        backend.inventory.append(extra)
        backend.set_position('yellow_block', [.7, 0, .675])
        before = copy.deepcopy(backend.inventory)
        with self.assertRaises(AgentError) as caught:
            self.agent(backend).invoke('stack_order', dict(order='BGR'))
        self.assertEqual(caught.exception.code, 'REARRANGEMENT_UNAVAILABLE')
        self.assertEqual(backend.inventory, before)
        self.assertEqual(backend.goals, [])

    def test_off_grid_partial_stack_is_cleared_before_base_relocation(self):
        backend = SceneBackend()
        backend.set_position('red_block', [.861, .232, .675])
        backend.set_position('green_block', [.861, .232, .725])
        result = self.agent(backend).invoke('stack_order', dict(order='RGB'))
        self.assertTrue(result['completed'])
        self.assertEqual([s['phase'] for s in result['steps']], ['dismantle', 'relocate_base', 'stack', 'stack'])
        self.assertEqual(backend.positions()['red_block'], [.55, -.28, .675])

    def test_complete_off_grid_tower_is_only_reverified(self):
        backend = SceneBackend()
        backend.tower(('red', 'green', 'blue'), [.861, .232, .675])
        result = self.agent(backend).invoke('stack_order', dict(order='RGB'))
        self.assertTrue(result['completed'])
        self.assertEqual(len(backend.goals), 2)
        self.assertTrue(all(s['already_complete'] for s in result['steps']))

    def test_invalid_staging_sites_fail_before_motion(self):
        for sites in ([], [[4, 0, .675]], [[.55, -.28, .675], [.56, -.28, .675]]):
            backend = SceneBackend()
            backend.tower(('red', 'green', 'blue'))
            self.config['agent_staging_positions'] = sites
            with self.assertRaises(AgentError) as caught:
                self.agent(backend).invoke('stack_order', dict(order='BGR'))
            self.assertEqual(caught.exception.code, 'REARRANGEMENT_UNAVAILABLE')
            self.assertEqual(backend.goals, [])

    def test_explicit_dismantle_from_any_block_in_tower(self):
        for selector in ('red', 'green', 'blue'):
            backend = SceneBackend()
            backend.tower(('red', 'green', 'blue'))
            agent = self.agent(backend)
            result = agent.invoke('dismantle', dict(block=selector))
            self.assertTrue(result['completed'])
            self.assertEqual([g['block'] for g in backend.goals], ['blue_block', 'green_block', 'red_block'])
            self.assertEqual(result['steps'][-1]['phase'], 'verify_base')
            self.assertTrue(all(len(support_chain(self.config, name, backend.positions())) == 1 for name in backend.positions()))
            backend.goals.clear()
            repeated = agent.invoke('dismantle', dict(block=selector))
            self.assertTrue(repeated['completed'])
            self.assertEqual(len(backend.goals), 1)
            self.assertTrue(repeated['steps'][0]['already_complete'])

    def test_non_rgb_blocker_is_staged_and_bystander_not_moved(self):
        self.config['agent_staging_positions'] = [b['position'] for b in self.config['blocks']]+[[.8, -.3, .675]]
        backend = SceneBackend()
        extra = copy.deepcopy(backend.inventory[0])
        extra.update(name='yellow_block', color='yellow')
        backend.inventory.append(extra)
        backend.set_position('yellow_block', [.55, -.28, .725])
        bystander = copy.deepcopy(extra)
        bystander['name'] = 'yellow_bystander'
        backend.inventory.append(bystander)
        backend.set_position('yellow_bystander', [.9, .4, .675])
        before = copy.deepcopy(bystander)
        result = self.agent(backend).invoke('stack_order', dict(order='RGB'))
        self.assertTrue(result['completed'])
        self.assertEqual(backend.goals[0]['block'], 'yellow_block')
        self.assertIn('target_pose', backend.goals[0])
        self.assertAlmostEqual(backend.positions()['yellow_block'][2], .675)
        self.assertEqual(bystander, before)
        self.assertNotIn('yellow_bystander', [g['block'] for g in backend.goals])

    def test_rotated_prefix_is_dismantled_before_rebuild(self):
        backend = SceneBackend()
        backend.tower(('red', 'green', 'blue'))
        backend.set_position('green_block', [.55, -.28, .725], yaw=.5)
        result = self.agent(backend).invoke('stack_order', dict(order='RGB'))
        self.assertTrue(result['completed'])
        self.assertEqual([g['block'] for g in backend.goals if 'target_pose' in g], ['blue_block', 'green_block'])
        self.assertAlmostEqual(backend.goals[1]['target_pose']['yaw'], .5)

    def test_preflight_reserves_all_slots_before_motion(self):
        backend = SceneBackend()
        backend.tower(('red', 'green', 'blue'))
        original = copy.deepcopy(backend.inventory)
        with patch('block_skills.rearrange.staging_position', side_effect=[[.7, 0, .675], ValueError('No staging space')]):
            with self.assertRaises(AgentError) as caught:
                self.agent(backend).invoke('stack_order', dict(order='BGR'))
        self.assertEqual(caught.exception.code, 'REARRANGEMENT_UNAVAILABLE')
        self.assertEqual(backend.goals, [])
        self.assertEqual(backend.inventory, original)

    def test_floating_scene_rejected_without_motion(self):
        backend = SceneBackend()
        backend.set_position('blue_block', [.7, 0, .9])
        with self.assertRaises(AgentError) as caught:
            self.agent(backend).invoke('stack_order', dict(order='RGB'))
        self.assertEqual(caught.exception.code, 'REARRANGEMENT_UNAVAILABLE')
        self.assertEqual(backend.goals, [])

    def test_dismantle_failure_stops_before_rebuild(self):
        backend = SceneBackend()
        backend.tower(('red', 'green', 'blue'))
        def failed(goal, cancel_event=None):
            backend.goals.append(goal)
            return dict(backend.result, success=False, verified=False, code='PLANNING_FAILED')
        backend.action = failed
        result = self.agent(backend).invoke('stack_order', dict(order='BGR'))
        self.assertFalse(result['completed'])
        self.assertEqual(result['steps'][0]['phase'], 'dismantle')
        self.assertEqual(len(backend.goals), 1)

    def test_cancel_during_action_stops_order_and_latches_held_fault(self):
        backend = SceneBackend()
        entered = threading.Event()
        def held_cancel(goal, cancel_event=None):
            backend.goals.append(goal)
            entered.set()
            if not cancel_event.wait(3):
                raise AssertionError('Cancellation did not reach transport')
            return dict(backend.result, success=False, verified=False, holding_block=True, code='CANCELED')
        backend.action = held_cancel
        agent, results = self.agent(backend), []
        thread = threading.Thread(target=lambda: results.append(agent.invoke('stack_order', dict(order='RGB'))))
        thread.start()
        try:
            self.assertTrue(entered.wait(2))
            request_id = agent.invoke('get_status', {})['active_request_id']
            with self.assertRaises(AgentError) as caught:
                agent.invoke('cancel', dict(request_id='0'*32))
            self.assertEqual(caught.exception.code, 'REQUEST_MISMATCH')
            cancellation = agent.invoke('cancel', dict(request_id=request_id))
            self.assertTrue(cancellation['cancel_requested'])
            self.assertFalse(cancellation['execution_stopped'])
        finally:
            if agent.active_request:
                agent.active_request['event'].set()
            thread.join(4)
        self.assertFalse(thread.is_alive())
        self.assertEqual(results[0]['code'], 'CANCELED')
        self.assertEqual(len(backend.goals), 1)
        self.assertIsNotNone(agent.fault)
        self.assertIsNone(agent.invoke('get_status', {})['active_request_id'])

    def test_cancel_between_steps_submits_no_next_goal(self):
        for cancel_after in (1, 2):
            backend = SceneBackend()
            agent = self.agent(backend)
            original = backend.action
            def cancel_after_success(goal, cancel_event=None):
                result = original(goal, cancel_event)
                if len(backend.goals) == cancel_after:
                    agent.invoke('cancel', dict(request_id=agent.active_request['request_id']))
                return result
            backend.action = cancel_after_success
            result = agent.invoke('stack_order', dict(order='RGB'))
            self.assertFalse(result['completed'])
            self.assertEqual(result['code'], 'CANCELED')
            self.assertEqual(len(backend.goals), cancel_after)
            self.assertTrue(result['steps'][0]['completed'])
            self.assertIsNone(agent.fault)

    def test_cancel_during_preflight_submits_no_goal(self):
        backend = SceneBackend()
        agent = self.agent(backend)
        original = backend.blocks
        def cancel_in_inventory():
            agent.invoke('cancel', dict(request_id=agent.active_request['request_id']))
            return original()
        backend.blocks = cancel_in_inventory
        result = agent.invoke('stack_order', dict(order='RGB'))
        self.assertEqual(result['code'], 'CANCELED')
        self.assertEqual(backend.goals, [])

    def test_timeout_keeps_completed_dismantle_reports(self):
        backend = SceneBackend()
        backend.tower(('red', 'green', 'blue'))
        agent = self.agent(backend)
        original = backend.action
        def timeout_on_second(goal, cancel_event=None):
            if backend.goals:
                raise TimeoutError('lost result')
            return original(goal, cancel_event)
        backend.action = timeout_on_second
        result = agent.invoke('stack_order', dict(order='BGR'))
        self.assertEqual(result['code'], 'EXECUTION_UNKNOWN')
        self.assertTrue(result['steps'][0]['completed'])
        self.assertEqual(result['steps'][0]['phase'], 'dismantle')
        self.assertIsNotNone(agent.fault)

    def test_cancel_idle_does_not_affect_future_request(self):
        backend = SceneBackend()
        agent = self.agent(backend)
        with self.assertRaises(AgentError) as caught:
            agent.invoke('cancel', dict(request_id='0'*32))
        self.assertEqual(caught.exception.code, 'NO_ACTIVE_REQUEST')
        self.assertTrue(agent.invoke('stack_order', dict(order='RGB'))['completed'])


if __name__ == '__main__':
    unittest.main()

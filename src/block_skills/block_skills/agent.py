"""Allowlisted ABot-Claw operations. ROS-independent policy, injectable transport."""
import math
import re
import threading
from pathlib import Path
import json
import uuid


class AgentError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def fail(code, message):
    raise AgentError(code, message)


def order_blocks(order):
    if isinstance(order, str):
        order = [dict(R='red', G='green', B='blue').get(c, '') for c in order.upper()]
    if (not isinstance(order, list) or len(order) != 3
            or any(not isinstance(c, str) for c in order)
            or set(order) != {'red', 'green', 'blue'}):
        fail('INVALID_ORDER', 'Use RGB, RBG, GRB, GBR, BRG, BGR or three distinct RGB colors, bottom to top.')
    return order


class Agent:
    schemas = {
        'get_status': (set(), set()), 'list_blocks': (set(), set()),
        'cancel': ({'request_id'}, {'request_id'}),
        'read_result': ({'task_id'}, {'task_id'}),
        'stack': ({'block', 'support'}, {'block', 'support', 'evidence'}),
        'pick_place': ({'block', 'target_pose'}, {'block', 'target_pose', 'evidence'}),
        'stack_order': ({'order'}, {'order', 'evidence'}),
        'dismantle': ({'block'}, {'block', 'evidence'}),
        'add_block': ({'color'}, {'color', 'name', 'seed'}),
    }

    def __init__(self, backend, artifact_dir, colors=('red', 'green', 'blue', 'yellow'), config=None):
        self.backend, self.root, self.colors = backend, Path(artifact_dir).resolve(), colors
        self.lock = threading.Lock()
        self.fault = None
        self.config = config
        self.state_lock = threading.Lock()
        self.active_request = None

    def cancel(self, request_id):
        with self.state_lock:
            active = self.active_request
            if active is None:
                fail('NO_ACTIVE_REQUEST', 'No adapter manipulation is active.')
            if request_id != active['request_id']:
                fail('REQUEST_MISMATCH', 'Request has changed; inspect get_status before canceling.')
            active['event'].set()
            return dict(success=True, completed=False, request_id=request_id, cancel_requested=True,
                        execution_stopped=False, message='Cancellation requested. Await the original execution result; this is not a stop confirmation.')

    def check_cancel(self):
        if self.active_request and self.active_request['event'].is_set():
            fail('CANCELED', 'Plan canceled; no further actions will be submitted.')

    def resolve(self, selector, blocks):
        if not isinstance(selector, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,63}', selector):
            fail('INVALID_BLOCK', 'Use an exact registered name or unique color.')
        exact = [b['name'] for b in blocks if b['name'] == selector]
        matches = exact or [b['name'] for b in blocks if b['color'] == selector]
        if len(matches) != 1:
            fail('AMBIGUOUS_BLOCK' if matches else 'UNKNOWN_BLOCK', selector)
        return matches[0]

    def completed(self, result, evidence):
        return (result.get('success') is True and result.get('verified') is True
                and result.get('holding_block') is False
                and (evidence != 'screenshot' or bool(result.get('evidence_files'))
                     and all(Path(p).is_file() for p in result['evidence_files'])))

    def action(self, goal):
        self.check_cancel()
        try:
            result = self.backend.action(goal, cancel_event=self.active_request['event'])
        except AgentError:
            raise
        except Exception:
            self.fault = 'Action transport failed: execution state uncertain; inspect ROS before recovery.'
            raise
        result = dict(result)
        result['completed'] = self.completed(result, goal['evidence'])
        if result.get('holding_block'):
            self.fault = 'Held block: restart simulation and adapter.'
        return result

    def invoke(self, operation, args):
        if operation not in self.schemas:
            fail('UNSUPPORTED_COMMAND', operation)
        required, allowed = self.schemas[operation]
        if not isinstance(args, dict) or not required <= args.keys() or args.keys() - allowed:
            fail('INVALID_REQUEST', 'Missing or unsupported arguments.')
        if operation == 'get_status':
            with self.state_lock:
                active = self.active_request
                state = dict(active_request_id=active['request_id'] if active else None,
                             cancel_requested=active['event'].is_set() if active else False)
            return dict(self.backend.status(), adapter_fault=self.fault, adapter_busy=self.lock.locked(), **state)
        if operation == 'cancel':
            if not isinstance(args['request_id'], str) or not re.fullmatch('[0-9a-f]{32}', args['request_id']):
                fail('INVALID_REQUEST', 'Use active_request_id returned by get_status.')
            return self.cancel(args['request_id'])
        if operation == 'read_result':
            task_id = args['task_id']
            if not isinstance(task_id, str) or not re.fullmatch('[0-9a-f]{32}', task_id):
                fail('INVALID_REQUEST', 'Invalid task ID.')
            path = (self.root / task_id / 'result.json').resolve()
            if self.root not in path.parents:
                fail('INVALID_REQUEST', 'Result outside artifact directory.')
            if not path.is_file():
                fail('RESULT_NOT_FOUND', task_id)
            return json.loads(path.read_text())
        if not self.lock.acquire(blocking=False):
            fail('BUSY', 'Wait for the current request; do not replay it.')
        try:
            if operation in ('stack', 'stack_order', 'dismantle', 'pick_place'):
                with self.state_lock:
                    self.active_request = dict(request_id=uuid.uuid4().hex, event=threading.Event())
            if self.fault:
                fail('RECOVERY_REQUIRED', self.fault)
            if operation == 'list_blocks':
                return self.backend.blocks()
            status = self.backend.status()
            if not status.get('success') or not re.fullmatch(
                    r'ready=True; busy=False; holding=none; fault=none', status.get('message', '')):
                fail('NOT_READY', status.get('message', 'Unknown skill state.'))
            evidence = args.get('evidence', 'none')
            if evidence not in ('none', 'screenshot'):
                fail('INVALID_REQUEST', 'evidence must be none or screenshot.')
            if operation == 'add_block':
                if not isinstance(args['color'], str) or args['color'] not in self.colors:
                    fail('INVALID_REQUEST', 'Unsupported color.')
                if 'name' in args and (not isinstance(args['name'], str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,63}', args['name'])):
                    fail('INVALID_REQUEST', 'Invalid name.')
                if 'seed' in args and (type(args['seed']) is not int or not 0 <= args['seed'] < 2**63):
                    fail('INVALID_REQUEST', 'seed must be a nonnegative int64.')
                return self.backend.add(args)
            blocks = self.backend.blocks()
            if operation in ('stack_order', 'dismantle'):
                from .rearrange import plan_order
                names = ([self.resolve(c, blocks) for c in order_blocks(args['order'])] if operation == 'stack_order'
                         else [self.resolve(args['block'], blocks)])
                goals = plan_order(self.config, blocks, names, evidence, dismantle=operation == 'dismantle')
                steps = []
                for goal in goals:
                    try:
                        result = self.action({k: v for k, v in goal.items() if k != 'phase'})
                    except AgentError as exc:
                        result = dict(success=False, completed=False, code=exc.code, message=str(exc))
                    except (TimeoutError, ConnectionError) as exc:
                        self.fault = 'Execution state uncertain: inspect ROS before recovery.'
                        result = dict(success=False, completed=False, code='EXECUTION_UNKNOWN', message=str(exc))
                    result['phase'] = goal['phase']
                    result['request_id'] = self.active_request['request_id']
                    steps.append(result)
                    if not result['completed']:
                        return dict(success=False, completed=False, code=result.get('code'), steps=steps,
                                    request_id=self.active_request['request_id'],
                                    message='Plan stopped; inspect the last result. No automatic retry.')
                if self.active_request['event'].is_set():
                    return dict(success=False, completed=False, code='CANCELED', steps=steps,
                                request_id=self.active_request['request_id'],
                                message='Cancellation arrived as the final step finished; inspect the completed step results.')
                return dict(success=True, completed=True, operation=operation, blocks=names, steps=steps,
                            **({'order': names} if operation == 'stack_order' else {}),
                            request_id=self.active_request['request_id'])
            block = self.resolve(args['block'], blocks)
            goal = dict(block=block, evidence=evidence)
            if operation == 'stack':
                goal['support'] = self.resolve(args['support'], blocks)
                if block == goal['support']:
                    fail('INVALID_REQUEST', 'A block cannot support itself.')
            else:
                pose = args['target_pose']
                if not isinstance(pose, dict) or set(pose) != {'x', 'y', 'z', 'yaw'} or any(
                        type(v) not in (int, float) or not math.isfinite(v) for v in pose.values()):
                    fail('INVALID_REQUEST', 'target_pose requires finite x,y,z,yaw in world; metres/radians.')
                goal['target_pose'] = pose
            result = self.action(goal)
            result['request_id'] = self.active_request['request_id']
            return result
        except (TimeoutError, ConnectionError) as exc:
            self.fault = 'Execution state uncertain: inspect ROS and restart adapter after recovery.'
            fail('EXECUTION_UNKNOWN', str(exc))
        finally:
            with self.state_lock:
                self.active_request = None
            self.lock.release()

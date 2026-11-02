"""ROS transport: one executor thread; no motion implementation."""
import math
import secrets
import threading

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.executors import SingleThreadedExecutor
from rosidl_runtime_py.convert import message_to_ordereddict
from block_interfaces.action import PickPlace
from block_interfaces.srv import Blocks
from std_srvs.srv import Trigger
from .agent import AgentError


class RosBackend:
    def __init__(self):
        self.node = Node('ur10e_sim_agent')
        self.status_client = self.node.create_client(Trigger, '/skills/status')
        self.blocks_client = self.node.create_client(Blocks, '/blocks')
        self.action_client = ActionClient(self.node, PickPlace, '/skills/pick_place')
        self.executor = SingleThreadedExecutor()
        self.executor.add_node(self.node)
        self.thread = threading.Thread(target=self.executor.spin, daemon=True)
        self.thread.start()

    def wait(self, future, timeout, cancel_event=None, handle=None):
        import time
        event = threading.Event()
        future.add_done_callback(lambda _: event.set())
        deadline, cancel_sent = time.monotonic()+timeout, False
        while not event.wait(min(.05, max(0, deadline-time.monotonic()))):
            if cancel_event is not None and cancel_event.is_set() and handle is not None and not cancel_sent:
                handle.cancel_goal_async()
                cancel_sent = True
            if time.monotonic() >= deadline:
                raise TimeoutError('ROS response timed out; execution may still be active. Do not retry.')
        return future.result()

    def service(self, client, request):
        if not client.wait_for_service(timeout_sec=5):
            raise AgentError('UNAVAILABLE', 'ROS service unavailable.')
        return self.wait(client.call_async(request), 60)

    def status(self):
        return dict(message_to_ordereddict(self.service(self.status_client, Trigger.Request())))

    def blocks(self):
        response = self.service(self.blocks_client, Blocks.Request(operation='list'))
        if not response.success:
            raise AgentError('BLOCK_SERVICE_FAILED', response.message)
        return [dict(message_to_ordereddict(b)) for b in response.blocks]

    def add(self, args):
        response = self.service(self.blocks_client, Blocks.Request(
            operation='spawn_random', color=args['color'], name=args.get('name', ''),
            seed=args.get('seed', secrets.randbits(63))))
        return dict(message_to_ordereddict(response))

    def action(self, goal, cancel_event=None):
        if cancel_event is not None and cancel_event.is_set():
            raise AgentError('CANCELED', 'Canceled before goal submission.')
        if not self.action_client.wait_for_server(timeout_sec=5):
            raise AgentError('UNAVAILABLE', 'Pick/place action unavailable.')
        request = PickPlace.Goal(block=goal['block'], evidence=goal['evidence'])
        request.support_block = goal.get('support', '')
        if 'target_pose' in goal:
            pose = goal['target_pose']
            request.target.header.frame_id = 'world'
            p, q = request.target.pose.position, request.target.pose.orientation
            p.x, p.y, p.z = float(pose['x']), float(pose['y']), float(pose['z'])
            q.z, q.w = math.sin(pose['yaw']/2), math.cos(pose['yaw']/2)
        def feedback(msg):
            f = msg.feedback
            self.node.get_logger().info(f'{f.progress:.0%} {f.stage}: {f.message}')
        if cancel_event is not None and cancel_event.is_set():
            raise AgentError('CANCELED', 'Canceled before goal submission.')
        handle = self.wait(self.action_client.send_goal_async(request, feedback_callback=feedback), 10)
        if not handle.accepted:
            raise AgentError('GOAL_REJECTED', 'Busy, not ready or recovery required. Inspect status.')
        future = handle.get_result_async()
        try:
            envelope = self.wait(future, 360, cancel_event=cancel_event, handle=handle)
        except TimeoutError:
            handle.cancel_goal_async()
            # Even a cancellation acknowledgement does not establish final state.
            raise
        result = dict(message_to_ordereddict(envelope.result))
        result['action_status'] = envelope.status
        if envelope.status != 4:
            result['success'] = False
        return result

    def close(self):
        self.executor.shutdown()
        self.thread.join(timeout=5)
        self.node.destroy_node()

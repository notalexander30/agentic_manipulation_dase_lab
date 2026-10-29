#!/usr/bin/env python3
"""Opt-in HTTP-to-ROS acceptance check for a supported Gazebo block scene."""
import argparse
import importlib.util
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true', help='Authorize simulated block manipulation')
    parser.add_argument('--order', choices=['RGB', 'RBG', 'GRB', 'GBR', 'BRG', 'BGR'], default='RGB')
    parser.add_argument('--evidence', choices=['none', 'screenshot'], default='none')
    args = parser.parse_args()
    path = Path(__file__).resolve().parents[1]/'openclaw-workspace/skills/ur10e-sim/scripts/ur10e_sim.py'
    spec = importlib.util.spec_from_file_location('ur10e_client', path)
    client = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(client)
    records = []
    def call(op, payload):
        result = client.invoke(op, payload)
        records.append(dict(operation=op, arguments=payload, result=result))
        print(json.dumps(records[-1], indent=2), flush=True)
        return result
    status = call('get_status', {})
    if (status.get('success') is not True or status.get('adapter_fault') or status.get('adapter_busy')
            or status.get('message') != 'ready=True; busy=False; holding=none; fault=none'):
        return 1
    inventory = call('list_blocks', {})
    if not isinstance(inventory, list):
        return 1
    if not args.execute:
        print('Read-only checks complete. --execute permits dismantling/rearranging the current scene.')
        return 0
    payload = dict(order=args.order, evidence=args.evidence)
    result = call('stack_order', payload)
    if result.get('completed') is not True:
        return 1
    for step in result['steps']:
        report = call('read_result', dict(task_id=step['task_id']))
        if not (report.get('success') is True and report.get('verified') is True and report.get('holding_block') is False):
            return 1
    # Repetition is an explicit acceptance case after verified success, not failure recovery.
    repeated = call('stack_order', payload)
    if repeated.get('completed') is not True or not all(s.get('already_complete') for s in repeated['steps']):
        return 1
    names = {c: c+'_block' for c in ('red', 'green', 'blue')}
    colors = dict(R='red', G='green', B='blue')
    protected = call('stack', dict(block=names[colors[args.order[0]]],
                                 support=names[colors[args.order[2]]], evidence=args.evidence))
    # A support-cycle or height check may reject before BLOCK_NOT_TOP.
    if protected.get('completed') or protected.get('success') is not False:
        return 1
    unknown = call('stack', dict(block='missing_block', support='red_block'))
    return 0 if unknown.get('code') == 'UNKNOWN_BLOCK' else 1


if __name__ == '__main__':
    raise SystemExit(main())

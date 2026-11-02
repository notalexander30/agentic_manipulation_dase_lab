#!/usr/bin/env python3
"""ABot-Claw UR10e simulation client; no ROS dependencies and no retries."""
import argparse
import json
import os
import sys
from urllib import request, error

OPERATIONS = ('get_status', 'list_blocks', 'pick_place', 'stack', 'stack_order', 'dismantle', 'cancel', 'add_block', 'read_result')


def invoke(operation, arguments, base_url=None, token=None):
    if operation not in OPERATIONS:
        raise ValueError('Unsupported operation')
    base_url = base_url or os.environ.get('UR10E_SIM_BASE_URL', 'http://127.0.0.1:8880')
    token = token or os.environ.get('UR10E_SIM_API_TOKEN', '')
    if not token:
        raise ValueError('Set UR10E_SIM_API_TOKEN')
    req = request.Request(base_url.rstrip('/') + '/tools/ur10e_sim/' + operation,
        data=json.dumps(arguments, allow_nan=False).encode(), method='POST',
        headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token})
    try:
        # Rearrangement permits up to eight complete ROS actions, plus services.
        with request.urlopen(req, timeout=3300 if operation in ('stack_order', 'dismantle') else 400) as response:
            return json.load(response)
    except error.HTTPError as exc:
        return json.loads(exc.read())
    except (error.URLError, TimeoutError, ConnectionError) as exc:
        return dict(success=False, completed=False, code='TRANSPORT_UNKNOWN',
                    message=f'{exc}; request may still be executing. Inspect status/logs; do not retry.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=OPERATIONS)
    parser.add_argument('arguments', nargs='?', default='{}', help='JSON object of typed arguments')
    args = parser.parse_args()
    try:
        result = invoke(args.operation, json.loads(args.arguments))
    except (ValueError, TypeError) as exc:
        result = dict(success=False, completed=False, code='INVALID_REQUEST', message=str(exc))
    print(json.dumps(result, indent=2))
    if args.operation in ('stack', 'pick_place', 'stack_order', 'dismantle'):
        return 0 if isinstance(result, dict) and result.get('completed') is True else 1
    return 1 if isinstance(result, dict) and result.get('success') is False else 0


if __name__ == '__main__':
    sys.exit(main())

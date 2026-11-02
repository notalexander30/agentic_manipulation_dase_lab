"""Small authenticated HTTP boundary for the simulator's typed skills."""
import argparse
import hmac
import json
import logging
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from .agent import Agent, AgentError


def make_server(agent, address, token):
    class Handler(BaseHTTPRequestHandler):
        def respond(self, status, body):
            data = json.dumps(body, allow_nan=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def authorized(self):
            if not hmac.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + token):
                self.respond(401, dict(success=False, code='UNAUTHORIZED'))
                return False
            return True

        def do_GET(self):
            if not self.authorized():
                return
            if self.path in ('/code/sdk', '/code/sdk/markdown', '/docs/guide/html'):
                self.respond(200, dict(robot='ur10e_sim', transport='POST /tools/ur10e_sim/OPERATION',
                    operations={k: dict(required=sorted(v[0]), allowed=sorted(v[1])) for k, v in Agent.schemas.items()},
                    completion='Require completed=true for manipulation. Inspect original success, verified, holding_block and evidence fields.',
                    ordering='RGB permutations are bottom to top. Stop on first failed step; never retry automatically.'))
            elif self.path == '/health':
                self.call('get_status', {})
            else:
                self.respond(404, dict(success=False, code='NOT_FOUND'))

        def call(self, operation, payload):
            try:
                self.respond(200, agent.invoke(operation, payload))
            except AgentError as exc:
                self.respond(409 if exc.code in ('BUSY', 'NOT_READY', 'RECOVERY_REQUIRED', 'EXECUTION_UNKNOWN') else 400,
                             dict(success=False, completed=False, code=exc.code, message=str(exc)))
            except Exception:
                logging.exception('Adapter operation failed')
                self.respond(500, dict(success=False, completed=False, code='INTERNAL_ERROR',
                                       message='Inspect adapter logs; do not automatically replay the request.'))

        def do_POST(self):
            if not self.authorized():
                return
            prefix = '/tools/ur10e_sim/'
            if not self.path.startswith(prefix):
                self.respond(404, dict(success=False, code='NOT_FOUND'))
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 16384:
                    raise ValueError('Body must be 1..16384 bytes.')
                payload = json.loads(self.rfile.read(length), parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))
            except (ValueError, UnicodeError) as exc:
                self.respond(400, dict(success=False, code='INVALID_REQUEST', message=str(exc)))
                return
            self.call(self.path[len(prefix):], payload)

    return ThreadingHTTPServer(address, Handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8880)
    parser.add_argument('--artifacts', default='/work/artifacts')
    parser.add_argument('--config', help='blocks.json used by the skill server (defaults to installed config)')
    args = parser.parse_args()
    token = os.environ.get('UR10E_SIM_API_TOKEN', '')
    if not token:
        parser.error('Set UR10E_SIM_API_TOKEN; use the same value in the OpenClaw client.')
    import rclpy
    from ament_index_python.packages import get_package_share_directory
    from pathlib import Path
    from .agent_ros import RosBackend
    rclpy.init(args=[])
    backend = RosBackend()
    from .geometry import load_config
    config = load_config(Path(args.config) if args.config else Path(get_package_share_directory('block_skills'))/'config'/'blocks.json')
    server = make_server(Agent(backend, args.artifacts, config['colors'], config=config), (args.host, args.port), token)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        backend.close()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

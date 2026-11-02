#!/usr/bin/env python3
"""Create this project's isolated OpenClaw config without model credentials."""
import argparse
import json
import os
from pathlib import Path
import secrets


def configure(root):
    root = Path(root).resolve()
    workspace = root/'openclaw-workspace'
    if not (workspace/'skills/ur10e-sim/SKILL.md').is_file():
        raise ValueError('UR10e workspace skill is missing.')
    ignore_path = root/'.gitignore'
    ignored = ignore_path.read_text(encoding='utf-8') if ignore_path.exists() else ''
    additions = [p for p in ('.openclaw-runtime/', '.openclaw-state/',
        'openclaw-workspace/memory/', 'openclaw-workspace/BOOTSTRAP.md',
        'openclaw-workspace/USER.md', 'openclaw-workspace/MEMORY.md') if p not in ignored.splitlines()]
    if additions:
        with ignore_path.open('a', encoding='utf-8') as stream:
            stream.write(('\n' if ignored and not ignored.endswith('\n') else '')+'\n'.join(additions)+'\n')
    state = root/'.openclaw-state'
    if state.is_symlink():
        raise ValueError('State directory must be local to this project, not a symlink.')
    state.mkdir(mode=0o700, exist_ok=True)
    path = state/'openclaw.json'
    if path.is_symlink():
        raise ValueError('Refusing to replace a symlinked config.')
    config = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    defaults = config.setdefault('agents', {}).setdefault('defaults', {})
    defaults['workspace'] = str(workspace)
    defaults.setdefault('timeoutSeconds', 3600)
    gateway = config.setdefault('gateway', {})
    gateway.setdefault('mode', 'local')
    gateway.setdefault('bind', 'loopback')
    gateway.setdefault('port', 18789)
    auth = gateway.setdefault('auth', {})
    auth.setdefault('mode', 'token')
    auth.setdefault('token', secrets.token_hex(32))
    tools = config.setdefault('tools', {})
    tools.setdefault('profile', 'coding')
    execution = tools.setdefault('exec', {})
    legacy_timeout = execution.pop('timeoutSec', 3450)
    execution.setdefault('timeoutSeconds', legacy_timeout)
    config.setdefault('skills', {}).setdefault('entries', {}).setdefault('ur10e-sim', {})['enabled'] = True
    temporary = state/'openclaw.json.tmp'
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as stream:
        json.dump(config, stream, indent=2)
        stream.write('\n')
    os.replace(temporary, path)
    if os.name != 'nt':
        state.chmod(0o700)
        path.chmod(0o600)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    path = configure(args.root)
    print(f'Project-local config ready: {path}')
    print('No model provider has been selected or authenticated by this script.')


if __name__ == '__main__':
    main()

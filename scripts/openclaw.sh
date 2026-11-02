#!/usr/bin/env bash
# Run the project-local OpenClaw instance in WSL/Linux.
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export OPENCLAW_STATE_DIR="$project_root/.openclaw-state"
export OPENCLAW_CONFIG_PATH="$OPENCLAW_STATE_DIR/openclaw.json"
export OPENCLAW_WORKSPACE_DIR="$project_root/openclaw-workspace"
export PATH="$project_root/.openclaw-runtime/bin:$project_root/.openclaw-runtime/tools/node/bin:$PATH"
export UR10E_SIM_BASE_URL="${UR10E_SIM_BASE_URL:-http://127.0.0.1:8880}"
if [[ -z "${UR10E_SIM_API_TOKEN:-}" && -r "$project_root/.container/agent-token" ]]; then
  UR10E_SIM_API_TOKEN="$(cat -- "$project_root/.container/agent-token")"
  export UR10E_SIM_API_TOKEN
fi
if [[ ! -x "$project_root/.openclaw-runtime/bin/openclaw" ]]; then
  echo 'Project-local OpenClaw is missing. Follow docs/OPENCLAW_LOCAL.md.' >&2
  exit 1
fi
cd -- "$OPENCLAW_WORKSPACE_DIR"
if [[ "${1:-}" == 'robot-check' ]]; then
  exec python3 "$OPENCLAW_WORKSPACE_DIR/skills/ur10e-sim/scripts/ur10e_sim.py" get_status
fi
exec "$project_root/.openclaw-runtime/bin/openclaw" "$@"

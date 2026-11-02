#!/usr/bin/env bash
# Install the tested OpenClaw release without touching global services/config.
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "$project_root/scripts/setup_openclaw.py"
mkdir -p -- "$project_root/artifacts/openclaw-setup"
installer="$project_root/artifacts/openclaw-setup/install-cli.sh"
curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 \
  https://openclaw.ai/install-cli.sh --output "$installer"
bash "$installer" --prefix "$project_root/.openclaw-runtime" \
  --version 2026.10.8 --node-version 24.22.1 --runtime-only --no-onboard
bash "$project_root/scripts/openclaw.sh" config validate
echo 'Runtime and workspace are ready. Choose/authenticate a model with:'
echo '  bash scripts/openclaw.sh onboard'

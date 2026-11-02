# Project-local ABot-Claw / OpenClaw

The UR10e project now contains its own OpenClaw runtime, state and ABot-Claw
workspace in the same WSL folder:

```text
abotclawpiper_lab/
  .openclaw-runtime/          installed OpenClaw and private Node (ignored)
  .openclaw-state/            config, gateway token, auth, sessions (ignored)
  .container/agent-token     existing simulator adapter token (ignored)
  openclaw-workspace/
    AGENTS.md                session startup and robot routing
    MISSION.md               ABot-Claw mission adapted for this simulator
    ROBOT.md                 ur10e_sim registry
    TOOLS.md                 client usage and completion rules
    HEARTBEAT.md             no autonomous robot activity
    skills/ur10e-sim/        typed HTTP client and skill
  scripts/openclaw.sh         wrapper for this isolated instance
  scripts/setup_openclaw.py   repeatable config preparation; no model credentials
  scripts/install_openclaw.sh repeatable project-local runtime installation
```

This is the existing ABot-Claw robot-specific skill/HTTP architecture running on
OpenClaw, with a simulator-specific mission. It is not an additional LLM or robot
controller implementation. The original ABot-Claw setup script is not used:
it targets a global workspace and physical fleet; this project uses local paths.

## Already configured on this WSL machine

The setup was deployed directly to
`/home/iliyas/projects/abotclawpiper_lab` in `Ubuntu-24.04`. OpenClaw
`2026.10.8 (dc2523e)` and private Node `24.22.1` were installed there. The CLI
validated the generated configuration and listed `ur10e-sim` as an eligible,
ready workspace skill. No model credentials were imported or selected.

The runtime, credentials and sessions are local to this project. The launcher
sets `OPENCLAW_STATE_DIR`, `OPENCLAW_CONFIG_PATH`, and `OPENCLAW_WORKSPACE_DIR`.
It also loads `UR10E_SIM_API_TOKEN` from the existing `.container/agent-token`
without printing it. Use the launcher for **all** project OpenClaw commands;
calling another global `openclaw` command can select a different installation.

## First model connection (interactive)

Keep the Gazebo simulation and HTTP adapter running as before. In WSL:

```bash
cd ~/projects/abotclawpiper_lab
bash scripts/openclaw.sh onboard
```

Select and authenticate your chosen model provider in OpenClaw's terminal/browser
flow. Do not paste keys into this chat. Onboarding may ask you to confirm the
existing project workspace; it should remain
`/home/iliyas/projects/abotclawpiper_lab/openclaw-workspace`. Keep the Gateway local
and bound to loopback. An additional daemon installation is not needed for this
foreground project workflow. Optional channels/memory imports are not needed.
Provider authentication is still required before natural-language commands can
be executed; skill discovery alone is not a working LLM connection.

The generated config uses the coding tool profile, a 3600-second agent deadline,
and a 3450-second exec deadline so multi-step robot requests can complete. The
installed release calls the exec setting `timeoutSeconds`; older examples using
`timeoutSec` are not valid for this release. Existing execution-approval policy
is not changed by the setup helper.

## Validate and operate

```bash
bash scripts/openclaw.sh config validate
bash scripts/openclaw.sh skills info ur10e-sim
bash scripts/openclaw.sh models status
bash scripts/openclaw.sh robot-check
```

`robot-check` is a project wrapper helper: it directly reads the adapter's status
using the same environment the agent inherits. It does not make an LLM call or
move the robot. It is not a native OpenClaw subcommand.

If onboarding has not already started this project's Gateway, start it in a
dedicated WSL terminal:

```bash
bash scripts/openclaw.sh gateway run
```

Do not start a second Gateway if the same instance is already running. In another
terminal, open the dashboard or terminal chat:

```bash
bash scripts/openclaw.sh dashboard
# Or use terminal chat:
bash scripts/openclaw.sh tui
```

Begin with "List the available blocks in the UR10e simulation." Confirm the
agent invokes the Python client and returns the actual inventory. Then ask
"Put blue on red" or "Rearrange the blocks into green-blue-red order, bottom to
top." Confirm the adapter terminal shows actual execution and the agent's reply
includes task IDs and verified outcomes. Do not let it replay a failed action.

For a scripted single turn through a running Gateway:

```bash
bash scripts/openclaw.sh agent --agent main \
  --message 'List the available blocks in the UR10e simulation.'
```

For cancellation, the skill must invoke the adapter's `cancel` operation with
the active request ID. Canceling the LLM turn or killing the Python client is
not confirmation that ROS stopped. Use a separate tracked invocation if needed
while a long robot request is running, then inspect the original final result.

## Reinstall or move to another project copy

Do not copy Linux runtime binaries from Windows or another architecture. Copy
the source workspace and scripts, then run in WSL/Linux:

```bash
bash scripts/install_openclaw.sh
```

This uses OpenClaw's official local-prefix installer, pinned to the release
validated here. It installs no global daemon and makes no robot requests.
`setup_openclaw.py` preserves existing model configuration and gateway tokens,
updates the workspace path, and ensures private state is excluded from Git.
It accepts JSON config; if an operator hand-edits it into JSON5, use OpenClaw's
config commands instead of rerunning the Python helper until it is valid JSON.

## Current acceptance status

Implemented and deployed: local runtime, isolated config, workspace routing,
automatic adapter token loading and reusable installation/launch helpers.
CLI version, config validation and live skill discovery passed in WSL.
The wrapper's live adapter check returned ready, idle, no held block and no
fault. Three setup regression tests passed both locally and in the ROS container.
Model authentication, actual LLM tool selection, and verified natural-language
manipulation remain pending until the user completes provider onboarding.

Sources: [ABot-Claw OpenClaw layer](https://github.com/amap-cvlab/ABot-Claw/tree/39c9ffc94a84f2e6baac431a9bff9771111f8539/openclaw_layer),
[OpenClaw local-prefix installer](https://docs.openclaw.ai/install/installer),
[workspace configuration](https://docs.openclaw.ai/concepts/agent-workspace),
and [CLI onboarding](https://docs.openclaw.ai/cli/onboard).

---
name: ur10e-sim
description: Control colored blocks with the simulated UR10e in Gazebo through ABot-Claw. Use for pick and place, tower dismantling, RGB rearrangement, and cancellation in the UR10e simulation.
---

Target robot type `ur10e_sim`. Uses Gazebo state and the existing ROS block skill
server, with no camera or physical robot driver requirement. Select this skill
for UR10e simulation commands in preference to the fleet's physical Piper route.

Use `python3 {baseDir}/scripts/ur10e_sim.py OPERATION 'JSON_ARGUMENTS'`.
The environment must contain `UR10E_SIM_BASE_URL` and `UR10E_SIM_API_TOKEN`.
Discover the robot contract at `GET /code/sdk` (Bearer token required).

First call `get_status` and `list_blocks`. Require readiness, no busy state,
no held block, and no fault. Resolve colors from the live inventory; if multiple
blocks share a color, ask which exact name to use. Do not guess coordinates.
For cancellation, call `get_status` only and use its `active_request_id`; cancel
must remain available while the robot is busy or holding a block.

Map user intent to these operations:

| Intent | Operation and JSON |
| --- | --- |
| Available blocks | `list_blocks {}` |
| Robot state | `get_status {}` |
| Put blue on red | `stack {"block":"blue","support":"red","evidence":"none"}` |
| RGB tower, bottom to top | `stack_order {"order":"RGB","evidence":"none"}` |
| Green-blue-red tower | `stack_order {"order":"GBR","evidence":"none"}` |
| Dismantle the tower containing red | `dismantle {"block":"red","evidence":"none"}` |
| Stop the active manipulation/plan | `cancel {"request_id":"ACTIVE_REQUEST_ID_FROM_STATUS"}` |
| Explicit coordinate placement | `pick_place {"block":"red","target_pose":{"x":0.82,"y":-0.28,"z":0.675,"yaw":0}}` |
| Add yellow | `add_block {"color":"yellow"}` |
| Read returned task ID | `read_result {"task_id":"RETURNED_32_HEX_ID"}` |

Accept all six RGB permutations, always bottom to top. `stack_order` inspects
the scene, preserves a correct bottom section, stages obstructing upper blocks
top to bottom, then builds and verifies the requested tower. `dismantle` stages
all upper blocks in the tower containing the selected block and reverifies its
base. Staging may also move a non-RGB block if it belongs to an affected tower.
Staging uses `agent_staging_positions` from blocks.json, or the configured
startup block positions when that setting is absent. There is no random fallback.
An incomplete requested tower with an off-site base is cleared and relocated
before building; an already-complete tower is only reverified. Operators must
validate configured locations with MoveIt and the full tower height.
Free configured positions are reserved before motion; lack of space or invalid poses
returns REARRANGEMENT_UNAVAILABLE without moving anything. These tools serialize
every ROS action and stop at the first incomplete result. Wait for the client
to finish before another mutation. Keep long calls in a tracked execution
session so user cancellation can be handled in a separate invocation; do not
fire and forget or retry manipulation.
Use `evidence:"screenshot"` only when requested and GUI capture is available.

For manipulation, report completion only if `completed=true`, `success=true`,
`verified=true`, `holding_block=false` and requested evidence exists. For an order,
inspect every entry in `steps`; include its task ID, report path and evidence paths.
`already_complete=true` means already placed and reverified without motion.
Action acceptance, service readiness and add-block success are not verified placement.

Preserve error codes/messages. Stop on BLOCK_NOT_TOP, STACK_LIMIT, planning or
execution errors, cancellation, missing evidence, or uncertain transport state.
For a requested RGB rearrangement, use `stack_order` rather than retrying a
failed single `stack`. Direct `stack` and `pick_place` retain support protection.
Held-block faults require a
simulation restart. Never automatically replay failed manipulation, including
evidence failures. After an operator resolves the issue, a new explicit request
can use the ROS idempotency check. Unsupported motions and raw joint/gripper
commands are outside this skill.

On “stop” or “cancel”, read the active request ID and invoke `cancel` with that
ID, even while busy. It cancels only this adapter's active manipulation, not
external ROS/manual operations. `cancel_requested=true` acknowledges the request;
`execution_stopped=false` means stopping is not confirmed. Monitor the original
execution session for its terminal ROS result and held-block state. Cancellation
can arrive too late to prevent a completed placement. A stale request ID must
not be retried against a new request without checking what the user intended.
Do not start another manipulation until the original request finishes and
status is healthy. Cancellation is not an emergency stop.

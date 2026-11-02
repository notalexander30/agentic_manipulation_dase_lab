# ABot-Claw UR10e simulation adapter

## Implementation and boundary

The new `block_skills agent` executable runs in the simulation container. Its
HTTP operations translate to the existing `/skills/status` Trigger service,
`/blocks` Blocks service, and `/skills/pick_place` PickPlace action. It does not
implement motion planning, grasping, target geometry or physical verification.
`add_block` uses `spawn_random`; direct spawn, move and randomize are not exposed.

`agent.py` owns validation, inventory resolution, serialization and cancellation.
`rearrange.py` sequences dismantling and rebuilding using the existing geometry
helpers; it does not plan robot motion. `agent_ros.py` owns ROS messages and an executor thread. `agent_http.py`
owns authenticated HTTP transport. The OpenClaw skill and standalone client are
under `openclaw-workspace/skills/ur10e-sim/`.

The architecture follows the original ABot-Claw robot-specific HTTP server,
fleet registry and SDK discovery pattern, and the PiPER-X workspace skill plus
Python HTTP client pattern. These are new UR10e routes, not a claim of a shared
upstream robot HTTP schema. Discovery aliases return JSON even at the legacy
`/markdown` and `/html` paths; there is no arbitrary `/code/execute` endpoint.

Sources inspected on 29 October 2026:

- [ABot-Claw ROBOT.md](https://github.com/amap-cvlab/ABot-Claw/blob/39c9ffc94a84f2e6baac431a9bff9771111f8539/openclaw_layer/ROBOT.md),
  run-robot-task skill, and robot agent SDK discovery source.
- [PiPER-X client](https://github.com/iliyas-tleuzhan/ABot-Claw-piperX/blob/HEAD/robot_layer/arm_piper_x/agent_server/run_piper_x_marker_task.py)
  and README: robot-specific client, environment URL/token, structured outcomes.
- [UR10e SDK](https://github.com/Charlotte-Li-0606/UR10e_WaterDrinking_Project/blob/HEAD/robot_layer/arm_ur10e/agent_server/robot_sdk/ur10e_sdk.py):
  ROS 2 MoveIt wrapper and backend boundaries. Its Jazzy feeding controller is
  not imported into this Humble/Robotiq simulation.
- [IFRA reference](https://github.com/IFRA-Cranfield/ros2_SimRealRobotControl):
  robot/gripper support. The simulation's existing pinned revisions remain intact.
- Local README, integration handoff, verification record, interfaces, CLI,
  skill server validation/execution/reporting, configuration and package metadata.

## Start on the Linux simulation host

Follow the existing README build and launch steps. Rebuild custom packages after
these changes so the new executable and dependency metadata are installed.
When creating the `ur10e` container, add this loopback port publication to its
existing Docker command:

```bash
-p 127.0.0.1:8880:8880
```

The port must be published at container creation. Run a single adapter instance.
Use the same ROS environment as the skill server (the image's domain 42 and
Cyclone DDS defaults). Do not launch physical robot drivers.

Set a shared token on the host, then start the adapter in a second terminal:

```bash
export UR10E_SIM_API_TOKEN="$(openssl rand -hex 32)"
docker exec -e UR10E_SIM_API_TOKEN="$UR10E_SIM_API_TOKEN" ur10e /entrypoint.sh \
  ros2 run block_skills agent --host 0.0.0.0 --port 8880 --artifacts /work/artifacts
```

Binding all container interfaces is needed for Docker port forwarding. The host
publication remains loopback. For a remote OpenClaw host, use an SSH tunnel or a
trusted authenticated network; this small server does not provide TLS.
Keep the adapter terminal for ROS feedback and HTTP logs. If desired, redirect
that command's output to a host log file. `docker logs ur10e` shows the simulation
launch logs, not necessarily output from a separate `docker exec` process.

The artifact root must match the skill server's configured artifact directory;
the default is `/work/artifacts`. No ROS dependency is needed on the agent host.
The adapter must also use the skill server's `blocks.json`; pass `--config PATH`
if the skill server uses a custom config instead of the installed default.

## Connect the active ABot-Claw workspace

For the project-local installation now included here, follow
[OPENCLAW_LOCAL.md](OPENCLAW_LOCAL.md). The manual merge instructions below are
for users who instead choose an existing external ABot-Claw workspace.

Copy `openclaw-workspace/skills/ur10e-sim` into the active OpenClaw workspace's
`skills/` directory, preserving its scripts folder. Merge the supplied
`ROBOT.ur10e_sim.md` entry into the active `ROBOT.md`, and extend any explicit
Piper/G1/Go2 selection in `MISSION.md` or the generic robot-task skill to select
`ur10e_sim` for simulation block tasks. Do not replace existing workspace files.
Restart/reload the agent as required by the installed OpenClaw version and
verify `ur10e-sim` appears in its skill inventory.

Set these variables in the actual OpenClaw process environment:

```bash
export UR10E_SIM_BASE_URL=http://127.0.0.1:8880
# Set UR10E_SIM_API_TOKEN to the same token used by the adapter.
```

Test the supplied client from this repository's root:

```bash
python3 openclaw-workspace/skills/ur10e-sim/scripts/ur10e_sim.py get_status
python3 openclaw-workspace/skills/ur10e-sim/scripts/ur10e_sim.py list_blocks
python3 openclaw-workspace/skills/ur10e-sim/scripts/ur10e_sim.py stack \
  '{"block":"blue","support":"red","evidence":"none"}'
```

Then issue natural-language requests in ABot-Claw: “Put the blue block on the red
block”, “Rearrange the existing tower into green-blue-red order, bottom to top”,
or “Dismantle the tower containing red.” The LLM maps those requests using the skill; no new LLM framework or
keyword parser is installed. Live skill discovery/routing must be tested in the
user's active OpenClaw installation before claiming natural-language success.

## HTTP and outcome contract

All routes require `Authorization: Bearer TOKEN`. `GET /health` reads status.
`GET /code/sdk` lists operations and allowed arguments. Invoke with
`POST /tools/ur10e_sim/OPERATION` and a JSON object:

| Operation | Arguments |
| --- | --- |
| get_status, list_blocks | `{}` |
| stack | `block`, `support`, optional `evidence` |
| pick_place | `block`, `target_pose:{x,y,z,yaw}`, optional `evidence` |
| stack_order | `order` (RGB permutation string or three RGB color names), optional `evidence` |
| dismantle | `block` identifying any block in the tower, optional `evidence` |
| cancel | `request_id` from `get_status.active_request_id` |
| add_block | `color`, optional `name`, `seed` |
| read_result | `task_id` |

Coordinates are block centres in world, metres and upright yaw in radians.
ROS performs reachability/workspace/collision validation. Colors must uniquely
identify a block, or use an exact registered name. Orders are bottom to top:
RGB runs green-on-red, then blue-on-green after clearing obstructing stacks.
All six permutations use that same rule. The request holds the adapter lock
across the whole plan, including dismantling.

The planner reads live poses, uses the existing support-chain and upright-pose
validation, and keeps an already-correct grounded section. It dismantles affected
towers top to bottom, physically picking each upper block onto a reserved free
table location. It includes non-RGB blockers in the affected towers and leaves
unrelated towers alone. All staging slots are checked against the configured
workspace/spacing and reserved before the first action. Slots come from
`agent_staging_positions` in blocks.json, defaulting to the three startup block
positions; there is no random fallback. A block's startup site is preferred when
free. Extra blocks may require more explicitly configured and runtime-tested
sites. No available space or
an invalid scene returns `REARRANGEMENT_UNAVAILABLE` before motion. MoveIt still
decides whether a reserved position is reachable; a planning failure stops the
plan without trying another position automatically. These sites are not a
kinematic guarantee. If the requested tower is incomplete and its base is
outside the configured sites, the planner clears it and relocates the base to
a free configured site before stacking. A complete requested tower is still
only reverified. Plans are limited to eight
actions and the configured upright cube/stack-height constraints.

`dismantle` lowers the upper blocks of the selected tower and reverifies its
base. Selecting any block in the tower identifies the same component. Repeating
it on an already-separated block reverifies that block without motion.

Single actions preserve all ROS result fields, adding `action_status` and
`completed`. Completion requires successful, verified placement, no held block
and existing screenshot files if requested. An order returns `steps`, each with
its ROS task ID/report/evidence and `phase` (`dismantle`, `relocate_base`, `stack`, or `verify_base`);
it stops immediately on an incomplete step. Pre-submission failures have no ROS
task ID. Plan responses preserve completed steps when a later action fails.
HTTP 200 means the operation returned a result, **not** that manipulation
succeeded. ROS failures retain their code/message. Policy errors use 400/409,
invalid credentials 401, unexpected errors 500. The client exits nonzero for
incomplete manipulation and never retries HTTP requests.

`add_block` success means scene creation only; it is not a verified placement.
Read durable ROS reports with `read_result` or inspect
`artifacts/TASK_ID/result.json` and `scene.png` on the host. Action feedback is
logged in the adapter terminal; the HTTP call waits for the final result.

## Reliability and recovery

- Manipulation and block creation serialize; competing requests receive BUSY.
  Status and report reads remain available while busy. Inventory reads also
  serialize because the underlying Blocks service rejects reads during motion.
- Existing stacks use the ROS idempotency verification, without motion when
  already complete. This is not an HTTP request-ID deduplication protocol.
- BLOCK_NOT_TOP, STACK_LIMIT, planning/execution failures and cancellation stop
  a plan; there are no automatic manipulation retries. Automatic dismantling is
  part of `stack_order`; a single `stack` retains the ROS support protection.
- A held-block result latches an adapter fault. Restart simulation and adapter
  after inspecting the report. A ROS transport timeout latches uncertain state;
  a result timeout requests cancellation, but does not assume cancellation
  succeeded. Inspect ROS before clearing uncertainty by adapter restart.
- An HTTP disconnect may lose the returned task ID while ROS continues. Inspect
  adapter logs and artifact timestamps; never automatically resubmit. There is
  currently no resumable HTTP job queue.
- Run one adapter. The ROS server independently prevents simultaneous actions
  from other clients, but direct CLI/manual clients can interleave between
  adapter plan steps. Keep them idle during an agent plan.
- Screenshot mode needs the existing GUI capture setup; default `none` uses
  state verification. Missing requested evidence prevents `completed=true`.

### Agent cancellation

Cancellation bypasses the manipulation lock and readiness checks. It targets
the active adapter request ID, covering the entire plan rather than just one
ROS step. In another terminal (or a separate tracked agent tool invocation):

```bash
python3 openclaw-workspace/skills/ur10e-sim/scripts/ur10e_sim.py get_status
python3 openclaw-workspace/skills/ur10e-sim/scripts/ur10e_sim.py cancel \
  '{"request_id":"COPY_ACTIVE_REQUEST_ID_FROM_STATUS"}'
```

The reply acknowledges `cancel_requested=true` and explicitly reports
`execution_stopped=false`. The transport requests ROS cancellation once a goal
handle is available, including cancellation arriving during goal acceptance.
It still waits for the terminal action result. The plan submits no subsequent
steps after cancellation. A late cancellation may race with successful placement;
the actual ROS result remains authoritative. Held-block cancellation latches
recovery just like any held-block fault. A cancellation timeout leaves execution
uncertain and blocks further mutations until recovery.

Idle cancellation returns `NO_ACTIVE_REQUEST`; stale IDs return
`REQUEST_MISMATCH` and cannot cancel a newer request. This does not cancel
external ROS goals or scene creation, and is not an emergency-stop interface.

## Tests and live acceptance

ROS-independent tests (Python standard library only):

```bash
PYTHONPATH=src/block_skills python3 -m unittest discover \
  -s src/block_skills/test -p 'test_agent*.py' -v
PYTHONPATH=src/block_skills python3 -m unittest discover \
  -s src/block_skills/test -p 'test_rearrange.py' -v
```

Also run the existing colcon tests in the container as documented in README.
`test_agent_ros.py` mocks ROS packages but exercises the actual message-mapping
code. It cannot establish generated-message compatibility or DDS behavior.

With simulation and adapter running, the opt-in HTTP-to-ROS check is:

```bash
python3 scripts/check_ur10e_agent.py
python3 scripts/check_ur10e_agent.py --execute --order RGB --evidence none
```

The second command moves simulated blocks. A fresh scene provides a baseline;
then repeat for RBG, GRB, GBR, BRG and BGR without resetting to exercise
rearrangement. Use `--evidence screenshot` for GUI acceptance. The check reads saved
reports, reissues a successful arrangement to test idempotency, and verifies
support protection and unknown-block rejection. Capture stdout as test evidence.
This script tests the client/HTTP/ROS boundary, not natural-language reasoning.

Finally execute the natural-language acceptance sequence in
[ABOTCLAW_INTEGRATION.md](ABOTCLAW_INTEGRATION.md#end-to-end-acceptance-test).
Ask ABot-Claw for all six orders, including transitions from an existing tower. Confirm each skill
invocation, final verified chain, report and evidence. Test BLOCK_NOT_TOP by
asking to place a bottom block at an explicit table coordinate while another
block rests on it. Use the existing simulation cancellation/planning-failure
checks to confirm errors remain errors through HTTP and the agent.
Also request a dismantle and confirm all affected blocks are individually
table-supported. During a subsequent plan, ask “cancel” and confirm the tool
returns promptly, no later steps start, and the original execution returns its
actual final result. Test both before grasp and while holding a block; the latter
must require simulation/adapter recovery. These live checks remain pending.

## Verification status

Implemented: adapter, ROS mapping, OpenClaw skill/client, fleet-entry fragment,
unit tests and opt-in live check. Rearrangement and agent cancellation are now
implemented and tested with mock ROS, including real localhost HTTP round trips.
The full available test suite reports **47 passed, 1 skipped**, with all 36
tower-to-tower RGB transitions exercised at each of the three default sites,
plus repeated-sequence and staging-exhaustion tests (the ROS node
construction test requires rclpy). The skill validator passes.
The ROS mapping uses mocked generated messages;
generated interfaces, colcon, Gazebo, GUI evidence, OpenClaw skill discovery,
LLM routing and natural-language end-to-end execution have **not** been run here.
This workspace has no Docker/ROS runtime. Historical simulation verification is
unchanged and does not verify this integration. Rearrangement requires supported
upright stacks, sufficient free table space and successful MoveIt planning.

### Reported WSL live tests and transport self-collision

The user's WSL/Docker run built both ROS packages and passed all 42 tests,
including ROS node construction. Supplied live output confirms blue-on-red,
rearrangement to RGB (including one dismantling move), reversal to BGR and a
subsequent RBG acceptance run. RGB output also confirms durable report reads,
idempotent verification and expected invalid/unknown-block rejection. This is
user-supplied runtime evidence, not execution on this Windows workspace.

The subsequent GRB run successfully staged green and blue, then failed while
transporting red onto green. Task `f23528f0edcf4c1fab6c5f071174bdcc` returned
`MOTION_FAILED`, MoveIt error -2, and `holding_block=true`. MoveIt explicitly
reported an invalid path with self-contact between `forearm_link` and
`robotiq_85_right_finger_link`, and refused to execute that transport trajectory.
Earlier grasp/lift movements had executed; the overall task therefore still
requires simulation and adapter restart for recovery. The plan stopped without
replaying manipulation. GBR and BRG were not reached in the loop.

As an initial mitigation, the launch reduces OMPL's
`longest_valid_segment_fraction` from 0.005 to 0.001 and TOTG `path_tolerance`
from its default 0.1 to 0.01. The former increases collision-check sampling;
the latter limits smoothing deviation. The logs establish the rejected
self-collision but do not establish which of these mechanisms produced it.
Final collision checking remains enabled. Planning may take longer. This
configuration change is syntax-checked only and **requires live validation**;
it is not evidence that GRB or every tower transition now succeeds.

Copy the updated `src/block_skills/launch/sim.launch.py` into the WSL working
copy, rebuild the custom packages, and restart the simulation and adapter.
Do not resume the held-block scene or automatically replay the failed action.
Retest from a fresh scene and then repeat the earlier order sequence to exercise
the accumulated arm configurations. Preserve new reports and MoveIt logs.

References: [OMPL collision-check resolution](https://moveit.picknik.ai/humble/doc/examples/ompl_interface/ompl_interface_tutorial.html)
and [Humble TOTG request-adapter parameters](https://github.com/moveit/moveit2/blob/humble/moveit_ros/planning/planning_request_adapter_plugins/src/add_time_optimal_parameterization.cpp).

### Second failure and fixed staging sites

The user confirmed the adjusted parameters were active (`ompl.path_tolerance`
0.01 and `ompl.ur10e_arm.longest_valid_segment_fraction` 0.001). Fresh-scene GRB
acceptance then passed. In a subsequent sequence RGB passed, but BGR failed on
the final red-on-green placement, task `1c2092bbb2f749cca42d2ec2ed2ebe37`.
This time the invalid path came from the Pilz LIN **lowering** step: many samples
collided between `table` and `upper_arm_link`. MoveIt refused execution of that
lowering trajectory; the prior grasp/lift/transport had executed and red remained
held. This is a different failure from the earlier OMPL transport self-collision.

Both affected targets were above a random staging site around `(0.861, 0.232)`.
The planner now uses fixed configured sites rather than sampling table positions
that later become tower bases. Default sites are the original three startup
positions. Off-site bases of incomplete towers are relocated after dismantling.
This removes position drift and makes workcell validation finite, but does not
prove any particular arm posture or trajectory will be collision-free. MoveIt
validation and held-block recovery remain unchanged. The previous OMPL tuning
does not address this Pilz lowering failure by itself.

This planner change passes stateful mock regressions, including 108 tower
transitions across the three sites and repeated order sequences; it has not yet
been run in Gazebo. Copy `block_skills/rearrange.py` and `test/test_rearrange.py`
under `src/block_skills/` into WSL, rebuild/test, and restart both simulation and
adapter before live testing. A fresh RGB-to-BGR run should stage only at startup
sites; inspect both placement success and the logged target coordinates.

# UR10e Lab 2: Agentic Block Manipulation with ABot-Claw

**Your goal:** connect a language model to OpenClaw, investigate how skills and
tools work, and ask ABot-Claw to build and rearrange a tower in Gazebo. Submit
the captures and answers listed in section 9.

Complete [Tutorial 1](TUTORIAL.md)
first. You should already be able to launch Gazebo, read block positions, and
pick and place blocks using coordinates. This continuation is intended for
fourth-year university students. You will compare those direct commands with
an agent that selects and invokes the supplied operations.

**Teaching draft:** this handout uses `combined-agentic-manipulation-lab`, which
combines Tutorial 1's staged launch and JSON loading with the agent integration.
Both tutorials, `compose.yaml`, the ROS packages and the OpenClaw helpers are in
this branch. Clone it below rather than using Tutorial 1's `lab-files.zip`, which
is not the agent installation bundle. The instructor must pilot the complete
merged model-to-Gazebo sequence and publish an agreed class revision before delivery.

Your window layout, model replies and block positions may differ from examples.
Use your own screenshots. Do not include API keys, login codes, gateway tokens
or authenticated dashboard URLs in captures.

## 1. Prepare the continuation workspace

Keep the files and captures from Tutorial 1. Stop its world and robot using
Tutorial 1 section 7, then leave its Docker shell with `exit`. Do not run two
Gazebo workcells in the same ROS domain during this lab.

### 1.1 Check the computer and model access

Run this section in an **Ubuntu desktop terminal** (**Ctrl+Alt+T**):

```bash
docker info
docker compose version
git --version
python3 --version
echo "$DISPLAY"
df -h .
```

Reuse the working Docker and desktop setup from Tutorial 1. Install only the
additional host tools if missing:

```bash
sudo apt update
sudo apt install -y curl ca-certificates python3 openssl
```

Before continuing, obtain the TA's approved **model provider, model name and
authentication method**. Use a model with tool-calling support. A provider's
API key and a consumer chat subscription are not automatically interchangeable;
use the login method that the provider and OpenClaw offer for this account.
The TA should confirm access and any usage budget before class.

This lab uses Ubuntu desktop and the GUI arrangement from Tutorial 1. WSL GUI
forwarding and remote model servers need a separate setup check with the TA.

### 1.2 Download the combined lab

**Ubuntu host terminal:**

```bash
cd ~
git clone --branch combined-agentic-manipulation-lab \
  https://github.com/notalexander30/agentic_manipulation_dase_lab.git \
  ur10e-agent-lab
cd ~/ur10e-agent-lab
git rev-parse --short HEAD
```

Record the revision in your report. If `ur10e-agent-lab` already exists, inspect
it with the TA instead of cloning over it or deleting it.

This checkout contains Tutorial 1's files together with:

- `openclaw-workspace/`: ABot-Claw's mission, robot registry and skills.
- `scripts/install_openclaw.sh`: installs a project-local OpenClaw runtime.
- `scripts/openclaw.sh`: selects this project's configuration and credentials.
- `src/block_skills/block_skills/agent_http.py`: the robot's HTTP adapter.
- `src/block_skills/block_skills/agent_ros.py`: calls the existing ROS interfaces.

You do not need to download a physical Piper driver or install ROS on Ubuntu.
ABot-Claw's robot-specific workspace and skill are supplied by this repository;
OpenClaw supplies the agent runtime.

### 1.3 Reuse the robot sources

The default Tutorial 1 workspace is `~/ur10e-skills-lab`. If yours has a different
name, adjust the source path below. The combined checkout already supplies
`compose.yaml`; keep that version rather than copying a file from an older lab.

```bash
cp -a ~/ur10e-skills-lab/upstream ./
test -f compose.yaml
```

The robot sources are separate copies; your Tutorial 1 workspace and edited JSON
remain unchanged. If the source directory is missing, complete Tutorial 1 setup
before continuing. Do not copy its `build/`, `install/`, credentials or `.xauth`
file. Inspect this checkout's Compose file: `lab` is the service, `ur10e:humble`
is the image, and `.:/work` shares this new workspace with Docker.

Use the pinned robot source revisions recorded in this branch's
[repositories.json](repositories.json):

```bash
git -C upstream/ros2_SimRealRobotControl checkout 9645e14a36cd7411871c9572275e6435ab41dac7
git -C upstream/IFRA_LinkAttacher checkout b056289ba93ccb549db98926dcbb9679642d0c8d
git -C upstream/gazebo_ros2_control checkout 9a3736cc742e73fc86355ef4fdb63326376ca1db
```

If Git reports local changes or a missing revision, ask the TA; do not discard
work with `reset --hard`. Start Lab 2 with this branch's default red, green and
blue blocks. The yellow and custom-color blocks from Tutorial 1 stay in that
earlier workspace. Extra objects can occupy staging sites needed for rebuilding.

### 1.4 Build and prepare desktop access

Still in the Ubuntu host terminal:

```bash
export LAB_UID=$(id -u) LAB_GID=$(id -g)
docker compose build
umask 077
touch .xauth
xauth nlist "$DISPLAY" | sed 's/^..../ffff/' | xauth -f .xauth nmerge -
test -s .xauth
mkdir -p .container artifacts/lab2
```

Create the adapter credential once for this workspace:

```bash
if [ ! -s .container/agent-token ]; then
  openssl rand -hex 32 > .container/agent-token
fi
chmod 600 .container/agent-token
```

This token authenticates the robot adapter. It is different from both a model
provider credential and OpenClaw's dashboard/gateway credential. Do not print it.

## 2. Connect the simulation to the agent adapter

### 2.1 Keep track of the terminals

| Terminal | Runs where? | Purpose |
| --- | --- | --- |
| A | Docker shell, `/work` | Build packages and keep Gazebo/MoveIt running |
| B | Ubuntu host, `~/ur10e-agent-lab` | Keep the HTTP adapter running through `docker exec` |
| C | Ubuntu host, `~/ur10e-agent-lab` | Install/authenticate OpenClaw, then run its Gateway |
| D | Ubuntu host, `~/ur10e-agent-lab` | Checks, dashboard and later command-line questions |

Open additional Ubuntu terminals with **Ctrl+Alt+T**. In each new host terminal,
run `cd ~/ur10e-agent-lab`. Do not run OpenClaw installation inside Docker.

### 2.2 Enter Docker and build the packages

In **Terminal A**, currently on the Ubuntu host:

```bash
docker compose run --rm \
  -p 127.0.0.1:8880:8880 \
  --name ur10e-agent-lab lab
```

You are now inside Docker at `/work`. Port `8880` lets the host's agent reach
the adapter in this container. Publishing it only on `127.0.0.1` keeps it local
to this computer. An earlier container without this mapping must be recreated;
starting another adapter alone does not publish its port.

**Terminal A — inside Docker:**

```bash
colcon build --base-paths src --symlink-install --parallel-workers 2
source /work/install/setup.bash
colcon test --base-paths src --event-handlers console_direct+
colcon test-result --verbose
```

**Expected:** Two packages build and the test summary has no errors or failures.
Stop and show the TA any failure before starting robot tasks.

### 2.3 Start the world, then the robot

Use the same staged sequence as Tutorial 1. First start the table world:

**Terminal A — inside Docker:**

```bash
ros2 launch block_skills world.launch.py \
  config:=/work/src/block_skills/config/blocks.json \
  > /work/artifacts/lab2/world.log 2>&1 &
WORLD_PID=$!
```

**Expected:** Gazebo shows the table and floor. Wait for this scene before
starting the robot. In the same Docker terminal:

```bash
ros2 launch block_skills robot.launch.py \
  config:=/work/src/block_skills/config/blocks.json \
  > /work/artifacts/lab2/robot.log 2>&1 &
ROBOT_PID=$!
ros2 run block_skills blocks status --wait 150
```

**Expected:** The UR10e and gripper appear and RViz opens. Status shows
`ready=True; busy=False; holding=none; fault=none`. The staged robot launch does
not load blocks automatically; readiness alone does not prove that objects exist.

Keep both stages running in this Docker shell. Do not start `sim.launch.py`
alongside them; the all-in-one launch would create another scene.

### 2.4 Load the blocks from JSON

**Terminal A — inside Docker:**

```bash
ros2 run block_skills blocks load
ros2 run block_skills blocks list
```

**Expected:** Three separate blocks appear and the inventory includes
`red_block`, `blue_block` and `green_block`. `load` adds missing names and keeps
existing blocks' live poses, as in Tutorial 1. Start this continuation with the
fresh checkout's three-block layout, not your earlier yellow/custom-block scene.

**Capture L2-1:** Gazebo's fresh scene and the successful build/readiness summary.

### 2.5 Start the HTTP adapter

**Terminal B — Ubuntu host:**

```bash
cd ~/ur10e-agent-lab
export UR10E_SIM_API_TOKEN="$(cat .container/agent-token)"
docker exec -e UR10E_SIM_API_TOKEN="$UR10E_SIM_API_TOKEN" \
  ur10e-agent-lab /entrypoint.sh \
  ros2 run block_skills agent --host 0.0.0.0 --port 8880 \
  --config /work/src/block_skills/config/blocks.json
```

Leave this terminal running. It shows ROS action feedback and HTTP requests.
The adapter translates validated operations into the existing ROS skills; it
does not implement another motion controller. Both server and adapter use the
same source `blocks.json` here. Complete block loading before starting the agent.
If you later change the staging layout or motion settings, stop and restart the
affected processes with the TA so server and adapter configuration stay aligned.
The agent's normal operation list does not expose Tutorial 1's `load` command.

## 3. Install OpenClaw and connect a model

### 3.1 Install the project-local runtime

**Terminal C — Ubuntu host:**

```bash
cd ~/ur10e-agent-lab
bash scripts/install_openclaw.sh
bash scripts/openclaw.sh --version
bash scripts/openclaw.sh config validate
bash scripts/openclaw.sh skills info ur10e-sim
bash scripts/openclaw.sh robot-check
```

The helper downloads the pinned OpenClaw release and a private Node runtime.
It also prepares this project's workspace and local configuration. It does
not select a model or install a global Gateway service.

**Expected:** The configuration is valid, `ur10e-sim` is available, and the
robot check reports ready, idle and no fault. The robot check makes no model
call and does not move anything. It tests the adapter connection independently.

### 3.2 Authenticate the model provider

**Terminal C — Ubuntu host:**

```bash
bash scripts/openclaw.sh onboard --classic \
  --skip-daemon --skip-bootstrap --skip-channels --skip-search --skip-ui
```

Follow the wizard using the TA-approved provider and model:

1. Select a **local Gateway** on this computer.
2. Keep the workspace at `~/ur10e-agent-lab/openclaw-workspace`.
3. Complete the provider's browser login or enter its credential when prompted.
4. Choose the assigned model and keep Gateway access on loopback.
5. Keep the supplied workspace files and skip optional messaging channels.

Use the interactive credential prompts; do not put API keys in a command,
`SKILL.md`, report or Git commit. A cloud-backed model does not require local
model-weight downloads. A TA-provided local model service needs its own running
server and connection details; the OpenClaw installer does not supply weights.

With daemon installation skipped, the wizard may report that the Gateway has
not been started. Start it explicitly in the next step.

```bash
bash scripts/openclaw.sh models status
bash scripts/openclaw.sh gateway run
```

Leave Terminal C running. If model status reports missing authentication or an
unavailable runtime/plugin, complete that provider's setup with the TA before
attempting robot movement. Do not switch to an unapproved paid model to bypass
an error. A saved model name alone is not proof of working inference.

### 3.3 Open the chat and test inference

**Terminal D — Ubuntu host:**

```bash
cd ~/ur10e-agent-lab
bash scripts/openclaw.sh dashboard
```

Use the project instance's browser chat. If the browser cannot open, use the
terminal interface instead: `bash scripts/openclaw.sh tui`.

**In the ABot-Claw chat**, ask:

> Explain the difference between planning a movement and verifying a placement.
> Do not move the robot or call a manipulation operation.

**Expected:** A real model reply, with no robot movement. If authentication,
quota, networking or tool access fails, record the error and ask the TA.

**Capture L2-2:** The selected provider/model and successful read-only chat reply.
Redact credential fields and token-bearing URLs. Record the OpenClaw version.

## 4. Investigate skills, tools and robot actions

### 4.1 Trace the request path

The language model decides what the user wants. OpenClaw gives it instructions
and callable tools. In this integration, the agent uses an execution tool to
run the supplied Python client, which calls the adapter:

```text
Your instruction in chat
  -> language model running through OpenClaw
  -> ur10e-sim skill instructions
  -> execution tool runs the supplied Python HTTP client
  -> adapter validates the structured request
  -> ROS skill action/service
  -> MoveIt, controllers and Gazebo
  -> placement verification and saved result
  -> agent's reply
```

In VS Code, open these files in your new workspace:

| File | What to investigate |
| --- | --- |
| `openclaw-workspace/MISSION.md` | Which robot is this agent asked to operate? |
| `openclaw-workspace/ROBOT.md` | Where is the adapter and what identifies it? |
| `openclaw-workspace/skills/ur10e-sim/SKILL.md` | When should the skill be used? What counts as completion? |
| `openclaw-workspace/skills/ur10e-sim/scripts/ur10e_sim.py` | How does a structured request reach HTTP? |
| `src/block_interfaces/action/PickPlace.action` | What are the goal, feedback and result fields? |

**Skill, tool and action are different terms.** An OpenClaw skill is an
instruction package; it does not create a robot controller or automatically
register every operation as a native OpenClaw tool. `exec`/`process` are runtime
tools. `stack` is an adapter operation invoked by the Python client.
`/skills/pick_place` is a ROS action with feedback and a terminal result.
The robot's executable skill is implemented by the ROS server.

### 4.2 Invoke a read-only operation directly

**Terminal D — Ubuntu host:**

```bash
export UR10E_SIM_API_TOKEN="$(cat .container/agent-token)"
export UR10E_SIM_BASE_URL=http://127.0.0.1:8880
python3 openclaw-workspace/skills/ur10e-sim/scripts/ur10e_sim.py list_blocks
```

Now ask **in chat**:

> Use the ur10e-sim skill to list the available blocks and their current
> positions. Do not move anything. State whether the robot is ready.

Compare the inventory with the direct client's output and Gazebo. Inspect the
chat's tool activity and Terminal B. A plausible description without a tool
call is not a live observation; ask the agent to obtain the actual inventory.

**Capture L2-3:** One read-only tool invocation, its result and the agent's reply.

**Answer:** Which layer chooses the block, which plans the arm movement, and
which checks the final placement? Why is skill discovery not proof of robot
connectivity or working model authentication?

## 5. Write and test a small read-only skill

Create `openclaw-workspace/skills/scene-observer/SKILL.md` in VS Code. You can
make the folder with this **Ubuntu host** command:

```bash
mkdir -p openclaw-workspace/skills/scene-observer
```

Use this starting content:

```markdown
---
name: scene-observer
description: Report the current UR10e simulation status and block inventory without moving anything.
---

When asked for a scene observation, run the existing client once for get_status
and once for list_blocks:
`python3 {baseDir}/../ur10e-sim/scripts/ur10e_sim.py get_status`
`python3 {baseDir}/../ur10e-sim/scripts/ur10e_sim.py list_blocks`

Report readiness, busy/fault/held-block state, block names and live positions
in metres. If a request fails, preserve its error and explain the observation
is incomplete. Do not guess positions or claim a tower was physically verified.
Do not invoke manipulation, spawning, cancellation or scene-reset operations.
```

Save the file. Add one useful reporting requirement of your own, such as
grouping returned exact names by color, without adding a motion command.
Check discovery in **Terminal D**:

```bash
bash scripts/openclaw.sh skills info scene-observer
```

Start a new chat session so it can load the new skill. Ask:

> Use the scene-observer skill to report the workcell. Do not move anything.

**Expected:** Live read-only calls and a report following your added requirement.
If the skill is missing, check the folder, frontmatter and discovery output
before continuing. A prompt instruction is not an enforced permission boundary;
this exercise changes instructions, not the agent's operating-system privileges.

**Capture L2-4:** Your skill file and the resulting read-only report.

**Answer:** What did adding this skill change? Did it add a new executable tool
or a new ROS capability? Which errors would a malformed skill file cause?

## 6. Ask ABot-Claw to pick and place blocks

### 6.1 Perform one manipulation from natural language

Check that the three blocks remain separate and the robot is ready. **In chat**:

> Put the blue block on the red block in the UR10e simulation. Wait for the
> verified result, then report the task ID. Use state verification, without
> requesting a screenshot from the adapter.

Watch Gazebo and Terminal B. Keep RViz's manual movement controls idle.
The agent should select `stack` with blue as the moving block and red as its
support. Do not type a ROS motion command or manually move the arm for this task.

**Expected:** Blue is on red. The result has `success=true`, `verified=true`,
`holding_block=false` and `completed=true`. `action_status=4` alone is not enough.
If the tool is still running, follow the existing process session; do not send
the same movement again because the first tool call has not returned yet.

**Capture L2-5:** Your prompt, the tool result/task ID and Gazebo's final scene.
Label the moving block and support in the caption.

### 6.2 Read the saved result

Ask the agent to read the result using the returned task ID. Also open
`artifacts/TASK_ID/result.json` in VS Code, replacing `TASK_ID` with the actual
32-character ID. `/work/artifacts/...` inside Docker is the same host folder
through the Compose volume.

Identify the requested block, support, final pose, verification samples and
held-block flag. In a direct action response the pose uses nested ROS fields;
the saved report uses its own readable pose representation. They describe the
same task. A default zero pose in a failed result is not a measured destination.

**Answer:** What evidence supports the agent's success statement? Why would
"request accepted" or the model saying "done" be insufficient?

## 7. Plan, build and rearrange towers through the agent

### 7.1 Predict the sequence before execution

The current scene has blue on red. **In chat**, first request a plan only:

> Without moving anything, explain how to change this scene into a red–green–blue
> tower, bottom to top. Identify any block that must be removed first.

Check the proposal against Gazebo. A sensible sequence clears blue from red,
places green on red, and then places blue on green. A plan-only reply must not
start a manipulation. Record whether the agent respected that instruction.

### 7.2 Execute the RGB order

Then ask:

> Build that red–green–blue tower, bottom to top, using the supplied stack_order
> operation. Use state verification and report each step's outcome and task ID.

The adapter plans dismantling and rebuilding using fixed staging sites and
serial ROS actions. The LLM does not calculate joint trajectories. It must wait
for verified results and stop on a failed step.

The coordinate-only restriction in Tutorial 1 was for learning block geometry.
Here you deliberately use the supplied stacking abstraction and compare the
responsibilities delegated to software.

### 7.3 Rearrange without resetting

Ask:

> Rearrange the existing tower into blue–green–red order, bottom to top. Do not
> reset or teleport the blocks. Use the existing skills and verify the result.

Observe which blocks move first and where they are staged. The configured
three-cube limit still applies. The adapter's fixed staging sites default to
the startup block positions; a valid table coordinate is not a guarantee of
collision-free arm motion. Failures remain valid experimental findings.

All six RGB permutations are supported as target orders:
`RGB`, `RBG`, `GRB`, `GBR`, `BRG`, `BGR`. The TA may assign one additional order
to each group; wait for the current plan to finish before changing it.

**Capture L2-6A:** The verified RGB tower and its tool trace.
**Capture L2-6B:** The rearranged BGR tower and the ordered step results.

**Answer:** Compare the sequence with your manual rearrangement in Tutorial 1.
Who decided the desired order, who reserved staging locations, and who planned
and verified each physical movement? Did you observe an unnecessary move?

## 8. Test verification, limits and recovery

### 8.1 Repeat an already-complete request

Ask for the same BGR order again. Inspect all step results.

**Expected:** The existing placements are reverified with
`already_complete=true`, without robot motion. Explain why the task can have a
new task ID even though no movement was needed. This is arrangement idempotency,
not a general promise to deduplicate every repeated HTTP request.

### 8.2 Compare model clarification with adapter validation

In a new chat, ask:

> I want one block on another. Ask me which blocks before moving anything.

Supply the missing names only after the agent asks. Do not authorize another
movement if doing so would interfere with the completed tower.

Then ask:

> Put the purple block on red. If no such block exists, report that and do not
> substitute another block or add one.

**Expected:** An inventory-based explanation that purple is unavailable, without
motion. The model may reject the request before sending it to the adapter.
That is different from receiving a structured adapter error.

To observe deterministic adapter validation, run this **Ubuntu host** check in
Terminal D. It requests an unknown name and should fail before motion:

```bash
python3 openclaw-workspace/skills/ur10e-sim/scripts/ur10e_sim.py stack \
  '{"block":"missing_block","support":"red_block","evidence":"none"}'
```

Expect `success=false`, `completed=false` and `code="UNKNOWN_BLOCK"`.
An unsupported name must not become a guessed object or an invented success.

**Capture L2-7:** The model's unavailable-object reply, structured rejection and
unchanged Gazebo scene. Also record the idempotency fields from section 8.1.

**Answer:** Which validation happened in the model's reasoning and which was
enforced by executable software? Why should both layers inspect the request?

### 8.3 Optional supervised dismantling and cancellation

Ask the TA before attempting cancellation. First request:

> Dismantle the tower containing blue. Put its upper blocks separately on the
> table and verify the base. Use state verification.

After it finishes, request a new tower. While it is running, ask the agent to
cancel the active adapter request. The agent must obtain `active_request_id`
and invoke `cancel` from a separate available tool execution context. If the
chat UI queues the message behind the active turn, tell the TA; do not assume
the robot has received it. The TA can use the documented direct cancel client
in another terminal to test the adapter independently.

`cancel_requested=true` acknowledges a request; it is not confirmation of a stop.
Read the original action's terminal result. Cancellation may arrive after a step
has completed or while a block is attached. A held-block result requires the
recovery below. Canceling an LLM reply or closing a client window is not a
robot emergency stop.

### 8.4 Diagnose a failed manipulation

If any task fails, preserve its `code`, `message`, `task_id`, completed steps and
`holding_block`. Do not automatically repeat the request or continue the plan.

| Observation | Next step |
| --- | --- |
| Unknown/ambiguous block | Inspect inventory and clarify the exact name |
| `REARRANGEMENT_UNAVAILABLE` | Check configured staging occupancy with the TA |
| `BLOCK_NOT_TOP` | Inspect the support chain; do not pick a supporting block directly |
| Planning/motion failure | Read simulation logs and the saved report; retain collision checking |
| `holding_block=true` or recovery fault | Stop tasks and restart both simulation and adapter with the TA |
| Transport timeout/disconnection | Determine whether the original task is still executing before resubmitting |

The world log is `artifacts/lab2/world.log`; the robot, MoveIt and skill-server
log is `artifacts/lab2/robot.log`. Save the relevant error lines and describe
what was already completed. The agent must report a partial or failed outcome
accurately, even if Gazebo appears close to the requested pose.

Manual **Print Screen** captures are sufficient for this draft. Automated
`evidence:"screenshot"` is a separate GUI/X11 acceptance check, not a substitute
for state verification. Do not request it until the TA confirms capture works.

## 9. Final task and submission

Using natural-language requests, build the TA-assigned RGB order, rearrange it
into a different assigned order without resetting, and ask for the saved results.
Do not enter joint angles, raw ROS motion commands or Gazebo state mutations.
You may clarify the intent and inspect failures rather than repeatedly rewording
a failed physical request until something happens.

Submit one Word report containing:

| Checkpoint | Evidence to submit |
| --- | --- |
| L2-1 | Package build/readiness and the fresh Gazebo scene; record Git revision |
| L2-2 | OpenClaw version, approved provider/model and successful read-only inference |
| L2-3 | Live inventory tool call and your request-path explanation |
| L2-4 | Your `scene-observer/SKILL.md`, added requirement and observed behavior |
| L2-5 | First natural-language placement, actual tool request/result, task ID and final scene |
| L2-6A/B | Two tower orders, ordered execution evidence and comparison with Tutorial 1 |
| L2-7 | Idempotency evidence and model/adapter rejection comparison |

Include the answers in sections 4–8, the skill file you wrote, and the final
tower's non-secret `result.json` reports. A multi-step request produces several
ROS task reports; identify which belongs to each movement. Do not submit
`.openclaw-state/`, `.openclaw-runtime/`, `.container/`, API keys or token files.

Finish with a short evaluation: Was the agent correct about the user's intent,
its tool selection, and the actual outcome? Give one limitation supported by
your observations. If a checkpoint is unfinished, include its error and what
you tried. An honest failed-result analysis is preferable to a success claim
without tool and scene evidence.

## 10. Stop the lab and recover a faulted scene

Wait for the active request to finish or for cancellation to reach a terminal
result. Preserve reports and log excerpts before resetting a faulted scene.

1. In the OpenClaw chat, finish the session. Stop the foreground Gateway in
   Terminal C with **Ctrl+C** after robot execution has settled.
2. Stop the adapter in Terminal B with **Ctrl+C**.
3. In Terminal A, still inside Docker, stop both launch stages:

```bash
kill -INT "$ROBOT_PID" "$WORLD_PID"
wait "$ROBOT_PID" "$WORLD_PID"
exit
```

The Compose run container is removed on exit; your host files and reports
remain. For held-block recovery, use this full shutdown with the TA and repeat
sections 1.4 and 2 from a fresh container, then restart the adapter and Gateway.
Reuse the credential file and model login; do not reinstall OpenClaw. Resetting
only the agent does not release a block attached in Gazebo.

## Instructor release and pilot checklist

This section is for planning the continuation, not an extra student task.

- Publish an immutable class tag/archive from `combined-agentic-manipulation-lab`
  containing both tutorials, Compose, the staged launch, explicit JSON loading,
  agent code and OpenClaw helpers. Replace the moving branch in the clone command
  with that agreed class revision when available. Do not distribute the older
  `lab-files.zip` alone as an agent-enabled release.
- Preserve Tutorial 1's coordinate-based exercises and submissions. This draft
  adds a new task sheet rather than changing `QUESTIONS.md` from Tutorial 1.
- Confirm the exact model/account method, tool access and budget on student
  accounts. A runtime with no authenticated provider is not a complete setup.
- Pilot GUI launching, model authentication, native tool approval prompts,
  inventory calls, two verified orders, idempotency, new-skill discovery and
  failure reporting. Confirm how cancellation is dispatched by the chosen UI.
- Check the staged handoff specifically: readiness after `robot.launch.py`,
  an initially empty inventory, then three objects after `blocks load`. Confirm
  the adapter and ROS server read the same source config. The combined source
  passed its available local unit tests; ROS-dependent checks were skipped when
  Docker was unavailable. That is not acceptance of the merged runtime workflow.
- Live development tests covered the HTTP/ROS path, six target orders in one
  fixed-site sequence, standalone dismantling and user-reported cancellation.
  These do not establish that this complete GUI/model-backed lesson has passed.
  Do not present the draft as classroom-validated before that pilot.
- Capture real agent-chat/tool screenshots after the pilot. No illustrative
  model reply or screenshot in this handout is claimed as executed evidence.
- Budget a practical session for setup verification, skill inspection/authoring,
  manipulation, rearrangement and result analysis. Pre-download/build before
  class where possible; measure timings during the pilot rather than assigning
  download waits as learning time.

Further references: [project-local OpenClaw setup](docs/OPENCLAW_LOCAL.md),
[robot adapter details](docs/UR10E_AGENT.md),
[OpenClaw installation](https://docs.openclaw.ai/install/installer),
[provider onboarding](https://docs.openclaw.ai/cli/onboard), and
[OpenClaw skills](https://docs.openclaw.ai/tools/skills).

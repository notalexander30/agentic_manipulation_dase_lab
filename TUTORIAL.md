# UR10e Lab: Pick, Place and Stack

**Your goal:** load a robot from GitHub, move blocks using coordinates,
and build a tower.

**Complete the six checkpoints below and ask the TA to check your results.
Include your screenshots and answers to Questions 1–8 in your report.
Part 7 is a bonus task.**

Use **Print Screen** (or **Fn + PrtSc**) on Ubuntu to capture your work.
Label each image with its checkpoint number.

**Final task overview** (3× speed):

<video controls width="800" preload="metadata" poster="docs/media/16-first-tower.png">
  <source src="docs/media/stack-overview.mp4" type="video/mp4">
</video>

Your window layout and block positions may look different from the examples below.

## 1. Prepare the workspace

Download the robot framework and prepare Docker, which runs Ubuntu 22.04 and
ROS 2 Humble in a container.

### 1.1 Install the tools

Run this section in an **Ubuntu desktop terminal** (**Ctrl+Alt+T**).
Copy commands only, without a terminal prompt such as `xander@computer:~$`.
Skip installation if these tools already work:

```bash
sudo apt update
sudo apt install -y git docker.io docker-compose-v2 xauth
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
```

`$USER` is your Linux username, for example `xander`. Check yours with:

```bash
whoami
```

Log out and back in before continuing.

If VS Code is not installed:

```bash
sudo snap install code --classic
```

### 1.2 Download the robot repositories

Create the workspace and download the robot packages once:

```bash
cd
mkdir ur10e-skills
cd ur10e-skills
mkdir upstream
git clone https://github.com/IFRA-Cranfield/ros2_SimRealRobotControl.git upstream/ros2_SimRealRobotControl
git clone https://github.com/IFRA-Cranfield/IFRA_LinkAttacher.git upstream/IFRA_LinkAttacher
git clone --branch humble https://github.com/ros-controls/gazebo_ros2_control.git upstream/gazebo_ros2_control
```

Source repositories:

- [ros2_SimRealRobotControl](https://github.com/IFRA-Cranfield/ros2_SimRealRobotControl): UR10e, gripper and MoveIt configuration.
- [IFRA_LinkAttacher](https://github.com/IFRA-Cranfield/IFRA_LinkAttacher): simulated grasp and release.
- [gazebo_ros2_control](https://github.com/ros-controls/gazebo_ros2_control): connects controllers to Gazebo joints.

### 1.3 Add the lab files

Download [lab-files.zip](lab-files.zip), then extract it into this workspace using **Files**.
Keep `upstream/`; place `src/`, `docker/` and `compose.yaml` beside it.

In VS Code's Explorer, the workspace should contain:

- `src/block_interfaces`: ROS task inputs and results.
- `src/block_skills`: the scene and robot skills.
- `docker/Dockerfile` and `docker/entrypoint.sh`: the Ubuntu and ROS environment.
- `compose.yaml`: the container's startup settings.

Open `compose.yaml`. The service is `lab`, the image is `ur10e:humble`, and
the `.:/work` volume shares your workspace with Docker. Saving an edit in
VS Code updates the same files the robot skills use.

### 1.4 Build the Docker image

Open the workspace and set your Linux account IDs:

```bash
code .
export LAB_UID=$(id -u) LAB_GID=$(id -g)
docker compose build
```

Copy `$(id -u)` and `$(id -g)` as written.

The image contains Ubuntu, ROS and the robot packages. Build it once.
This creates the image; it does not start the robot.

![Docker image build completed](docs/media/01-docker-build.png)

### 1.5 Give the container desktop access

Allow Docker's Gazebo and RViz windows to use your desktop:

```bash
umask 077
touch .xauth
xauth nlist "$DISPLAY" | sed 's/^..../ffff/' | xauth -f .xauth nmerge -
```

`$DISPLAY` is supplied by your desktop session, for example `:0` or `:1`.
Keep `"$DISPLAY"` as written; do not replace it with your username.

### 1.6 Enter Docker and build the skill packages

In the same terminal:

```bash
docker compose run --rm lab
```

`lab` selects the Compose service. `--rm` removes the container when you exit;
your workspace files remain on Ubuntu.

You are now at `/work` **inside Docker**. Keep this terminal open for all
remaining ROS commands; edit files in your Ubuntu VS Code window.

```bash
colcon build --base-paths src --symlink-install --parallel-workers 2
source /work/install/setup.bash
```

`source` loads the workspace environment so this terminal can find the packages
you built.

![Both custom ROS packages finished building](docs/media/02-package-build.png)

`colcon` builds the two custom packages. The IFRA robot packages are already
inside the Docker image.

### 1.7 Checkpoints and Questions

#### Checkpoints

Show the TA the successful build. Include one terminal screenshot showing
`block_interfaces`, `block_skills` and `2 packages finished` in your report.

#### Questions

1. What is the purpose of sourcing the workspace, and why is it needed?

## 2. Start the simulation and move joints manually

Gazebo simulates physics and moving objects. RViz shows ROS data and MoveIt
planning controls. Simulation lets you test layouts and robot motion without
physical hardware. Load the table, robot and blocks separately.

### 2.1 Prepare the scene settings

In VS Code, open `src/block_skills/config/blocks.json`. The `table` entry sets
the table dimensions; `blocks` contains the objects you will add later.
Keep this file open while working with the simulation.

### 2.2 Open Gazebo with the table

In the Docker terminal, export the table from JSON and open Gazebo:

```bash
python3 -m block_skills.geometry /work/src/block_skills/config/blocks.json /tmp/table.world
gazebo /tmp/table.world -s libgazebo_ros_init.so -s libgazebo_ros_factory.so > /tmp/world.log 2>&1 &
WORLD_PID=$!
```

`$!` automatically gives the process ID of the command started with `&`.
`WORLD_PID` saves the Gazebo process ID. Copy this line unchanged.

The `-s` options enable ROS communication and robot spawning.

**Expected:** Gazebo shows a table and floor, with no robot or blocks yet.
The table dimensions come from JSON. Wait for the table before continuing.
Zoom in on the table if needed.

![Gazebo world containing the table before the robot is loaded](docs/media/03-table-world.png)

### 2.3 Start the arm, gripper and RViz

The robot stage connects the supplied UR10e model, controllers and MoveIt to
the Gazebo world. It also opens RViz with the planning controls configured.
In the same Docker terminal:

```bash
ros2 launch block_skills robot.launch.py config:=/work/src/block_skills/config/blocks.json > /tmp/robot.log 2>&1 &
ROBOT_PID=$!
ros2 run block_skills blocks status --wait 150
```

`ROBOT_PID` saves the robot launch process ID. Keep `$!` unchanged.

Wait for readiness before moving. Gazebo simulates the robot; RViz provides
MoveIt planning controls. `&` leaves the terminal available.

![UR10e and gripper loaded into the empty table world](docs/media/04-robot-loaded.png)

![MoveIt planning controls and the robot in RViz](docs/media/05-rviz.png)

Keep Gazebo and the robot launch running in this shell. The saved process IDs
let you stop them later.

### 2.4 Plan and move the arm in RViz

In RViz, select **Planning Group → ur10e_arm**, **Start State → current**,
then open **Joints**. Enter each joint's absolute goal from the table.
Leave the gripper unchanged.

| Arm joint | Pose A (degrees) | Pose B (degrees) |
| --- | ---: | ---: |
| `shoulder_pan_joint` | 15° | 30° |
| `shoulder_lift_joint` | −75° | −60° |
| `elbow_joint` | 15° | 30° |
| `wrist_1_joint` | −75° | −60° |
| `wrist_2_joint` | 15° | 30° |
| `wrist_3_joint` | 15° | 30° |

If RViz shows radians, use `0.2618` for 15°, `-1.3090` for −75°,
`0.5236` for 30°, and `-1.0472` for −60°. Use the unit shown by RViz.
These are absolute goals, not increments. After executing each pose, save
one joint-state message using:

```bash
ros2 topic echo /joint_states --once
```

Complete A, then B:

1. **Manually type all six joint goals** in the Joints tab.
2. Click **Plan** and inspect the path. Gazebo's arm has not moved yet.
3. **Capture 2A-before / 2B-before:** RViz showing all six goal values and the
   planned path, with Gazebo showing the arm before execution.
4. Click **Execute** after a successful plan.
5. **Capture 2A-after / 2B-after:** Gazebo showing the executed pose; include
   RViz's current joint values in the same capture if possible. Save the
   joint-state message after each execution.
6. Before planning B, refresh **Start State → current**.

For submission, enter both sets manually and label the captures **Pose A**
and **Pose B**. Keep collision checking enabled and execute only successful
plans. If planning fails, capture the goal values and error, then ask the TA
before continuing. Finish manual joint movement before loading blocks.

Before executing a movement (illustrative example; use your assigned angles):

![Arm before MoveIt execution](docs/media/25-moveit-plan.png)

After MoveIt executes the movement:

![Arm after MoveIt execution](docs/media/26-moveit-executed.png)

The goal model previews the requested pose; Execute sends the planned motion
to the controllers. Later, your `pick` commands send block destinations to
the same planning system instead of specifying individual joint angles.

### 2.5 Read ROS output

A ROS node is a running program. `/move_group` handles motion planning.
`/joint_states` publishes joint names and positions; each name matches the
position at the same array index. Arm joint positions are in radians.

In the Docker terminal, enter:

```bash
ros2 node list
```

Keep this output with the joint-state messages recorded after Pose A and Pose B.

### 2.6 Checkpoints and Questions

#### Checkpoints

Show the TA both executed poses. Include the before/after captures for A and B,
the node-list output and the two joint-state messages in your report.

#### Questions

2. Record the output of `ros2 node list`. Which node handles motion planning?
3. What is Gazebo used for in this lab, and what is RViz used for?

## 3. Edit and load JSON blocks

### 3.1 Find the source files

In VS Code, look under `src/`:

- `block_skills/block_skills/cli.py`: reads your commands.
- `block_interfaces/action/PickPlace.action`: task inputs and results.
- `block_skills/block_skills/server.py`: plans and executes tasks.
- `block_skills/block_skills/geometry.py`: scene geometry and position checks.
- `block_skills/config/blocks.json`: positions, colors and motion settings.

### 3.2 Inspect and edit the block definitions

In VS Code, open `src/block_skills/config/blocks.json`. Its `blocks` list
defines each block's unique `name`, `color`, centre `position` in
metres `[x, y, z]`, and `yaw` in radians.

The starting list is:

```json
"blocks": [
  {"name": "red_block", "color": "red", "position": [0.55, -0.28, 0.675], "yaw": 0.0},
  {"name": "blue_block", "color": "blue", "position": [0.70, 0.0, 0.675], "yaw": 0.0},
  {"name": "green_block", "color": "green", "position": [0.55, 0.28, 0.675], "yaw": 0.0}
]
```

Before the first load, change green's position to `[0.65, 0.28, 0.675]` and
its palette entry to `"green": "#1AE666"`. Save the file.

Colors accept six-digit hex codes in quotes, such as `"#1AE666"`.
The supplied blocks use palette keys (`red`, `blue`, `green`); for a new block,
you can put a hex code directly in its `color` field as shown in section 5.
Keep JSON commas and braces intact, and save with **Ctrl+S**.

### 3.3 Load the configured blocks into Gazebo

```bash
ros2 run block_skills blocks load
ros2 run block_skills blocks list
```

**Expected:** Three blocks appear, with green at approximately
`[0.65, 0.28, 0.675]`. The server reads JSON, creates the cube models in
Gazebo, and adds their collision geometry to MoveIt. They are separate objects,
not links added to the robot URDF.

![Three blocks loaded from the edited JSON](docs/media/07-json-blocks.png)

![Current block centres read from Gazebo](docs/media/08-live-poses.png)

### 3.4 Apply changes to existing blocks

`load` adds missing model names; it preserves existing blocks' poses and colors.
To apply changed starting positions or colors, stop Gazebo and the robot launch
using section 8 (stay inside Docker), repeat sections 2.2–2.3, and load again.
Keep Z at `0.675`, stay within `workspace`, and leave at least `0.16 m`
between separate block centres.

![Restarted scene with an edited starting position loaded](docs/media/22-reloaded-scene.png)

### 3.5 Checkpoints and Questions

#### Checkpoints

Show the TA the edited green block and the three loaded blocks. Include the
JSON edits and the resulting Gazebo scene in your report.

#### Questions

4. Which lines did you modify in `blocks.json`? Show the position and color
   entries before and after your changes.
5. Why is simulation useful before testing a robot task on real hardware?

## 4. Pick and place with coordinates

### 4.1 Read the position and dimensions

Positions are `[x, y, z]` in metres. X follows Gazebo's red world axis,
Y the green axis, and Z the blue axis. Use the world axes, not the direction
the camera is facing. The `world` frame is the shared coordinate reference
for the robot and blocks. MoveIt checks for collisions along the planned path.

The table measures **0.90 m (X) × 1.20 m (Y) × 0.10 m thick**. Its top is at
**Z = 0.65 m**. Each block is **0.05 m × 0.05 m × 0.05 m**; its centre rests
at **Z = 0.675 m**.

### 4.2 Choose a destination and run the placement

First read the available block names and their current positions:

```bash
ros2 run block_skills blocks list
```

Set the block name and destination. These example values move red to a clear
table position; change the values after `=` for your own task:

```bash
BLOCK="red_block"
X=0.82
Y=-0.28
Z=0.675
```

Use the variables in the command:

```bash
ros2 run block_skills blocks pick "$BLOCK" "$X" "$Y" "$Z"
```

Change the values above, then reuse the command. `pick` reads the block's
current pose from Gazebo and places it at XYZ.

Use X = `0.38–0.95`, Y = `-0.45–0.45`, and Z = `0.675` for the table.
Leave at least `0.16 m` between centres and wait for `success: true`.
If a failure reports `holding_block: true`, restart before another task.

### 4.3 Move each block

Move red by changing X, blue by changing Y, and green by changing both X and Y.
Update `BLOCK`, `X`, `Y` and `Z` before each move, then run the same `pick`
command. Read `blocks list` after each placement.

### 4.4 Checkpoints and Questions

#### Checkpoints

Show the TA the three moved blocks. Include one screenshot of the scene and
the variable values and command used for each move.

#### Questions

6. Why is a common coordinate frame needed when specifying robot and block
   positions?
7. Why must the planned path be checked for collisions even when the
   destination is clear?

## 5. Add and move your own colored block

### 5.1 Choose a color and add a block

Open the [HEX color picker](https://htmlcolorcodes.com/color-picker/), choose
your own color, and copy its six-digit **#RRGGBB** code, including `#`.
Each pair sets the red, green and blue intensity.

In VS Code, add a fourth entry to the `blocks` list in
`src/block_skills/config/blocks.json`. Keep a comma between entries:

```json
{"name": "extra_block", "color": "#FF8800", "position": [0.55, 0.12, 0.675], "yaw": 0.0}
```

Replace `#FF8800` with your own chosen code, in quotes. Choose a color distinct
from the three existing blocks; use your own code rather than copying this
example. `extra_block` is the model name used in commands. A direct hex code
needs no new entry in the `colors` dictionary.

Choose a starting position clear of both the live blocks and the other JSON
starting positions. Save, then run:

```bash
ros2 run block_skills blocks load
```

**Expected:** One new block appears in your chosen color; existing blocks keep
their live poses. Adding a scene object does not move the robot arm.

Example of a fourth block; your chosen color will differ:

![Example of a fourth block added through JSON](docs/media/12-yellow-loaded.png)

### 5.2 Move the added block

Move it to a clear table position using `pick`, for example:

```bash
BLOCK="extra_block"
X=0.85
Y=0.30
Z=0.675
ros2 run block_skills blocks pick "$BLOCK" "$X" "$Y" "$Z"
```

Keep your added block separate from the tower.

![Example of the added block after a robot placement](docs/media/13-yellow-place.png)

### 5.3 Checkpoints and Questions

#### Checkpoints

Show the TA your new block after its robot placement. Include one screenshot
showing the four blocks in Gazebo, and write your chosen hex code below it.

#### Questions

8. What do the three pairs in a `#RRGGBB` color code represent?

## 6. Build a tower with your own colors

### 6.1 Choose the colors and arrangement

Choose three distinct colors other than red, green or blue. In `blocks.json`,
replace each original block's `color` value with your chosen hex code. Keep the
model names unchanged and choose colors different from your fourth block.

Restart Gazebo and the robot, then load the blocks again as in section 3.4.
Build one three-block tower at your chosen location and in your chosen order.
Use `pick` with calculated block-centre coordinates, without the `stack` shortcut.
Keep the fourth block separate.

### 6.2 Checkpoints

Show the TA your tower. Submit **one screenshot** of the completed arrangement.
Below it, list the three hex colors and block-centre coordinates, bottom to top.

## 7. Bonus: five colors in a horizontal row

Add a fifth block using another distinct hex color of your choice. Use the
robot to arrange all five blocks in one horizontal row on the table.

*Hint: unique model names, block centres and workspace limits.*

### 7.1 Checkpoints

Submit two screenshots: one showing the added fifth color, and one showing
the completed row of five blocks.

## 8. Stop the simulation

In the same Docker terminal:

```bash
kill -INT "$ROBOT_PID" "$WORLD_PID"
wait "$ROBOT_PID" "$WORLD_PID"
```

Keep both variable names unchanged. They expand to the process IDs saved in
sections 2.2–2.3. Run these commands in the same Docker terminal; do not
replace them with your username or type guessed process numbers.

Use `exit` to leave Docker when finished. Your workspace files remain on Ubuntu.
For another session, export the account IDs and prepare desktop access as in
section 1, enter Docker, source the packages, then launch the world and robot
and load the blocks again.

Submit your Word report with checkpoints 1–6, answers to Questions 1–8, and your
edited `blocks.json`. Include the bonus screenshots if you attempted Part 7.

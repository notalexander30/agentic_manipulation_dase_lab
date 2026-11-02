# UR10e Lab: Submission Checkpoints

Complete the checkpoints in order using [TUTORIAL.md](TUTORIAL.md).
Submit one Word report containing the captures and answers below, together
with your edited `src/block_skills/config/blocks.json`.

Take your own screenshots with **Print Screen** (or **Fn + PrtSc**) on Ubuntu.
Insert the saved images from **Pictures → Screenshots** into your report and
label each one with its checkpoint number.

## Checkpoint 1: Build the packages

**Submit:** One terminal screenshot showing `2 packages finished` after building
`block_interfaces` and `block_skills` inside Docker.

**Answer:** Why must you run `source /work/install/setup.bash` before using the
packages you built?


## Checkpoint 2: Move the robot manually with MoveIt

In RViz, select `ur10e_arm` and set Start State to current. Manually set all six
arm joints: `shoulder_pan_joint`, `shoulder_lift_joint`, `elbow_joint`,
`wrist_1_joint`, `wrist_2_joint` and `wrist_3_joint`. Leave the gripper unchanged.
Complete these absolute goals in order:

1. **All six joints at 45° (0.7854 rad each):** Enter the goals, click Plan,
   capture the plan and the arm before execution, then click Execute and
   capture the resulting pose in Gazebo.
2. **All six joints at 90° (1.5708 rad each):** Refresh Start State to current,
   enter the new goals, and repeat Plan, capture, Execute, capture.

Enter the value matching the unit shown by RViz. Execute only a successful plan.

**Submit:** Four screenshots:

- **2A-before:** RViz showing all six 45° goals and the planned path, with
  Gazebo showing the arm before execution.
- **2A-after:** Gazebo showing the pose after executing the 45° goals.
- **2B-before:** RViz showing all six 90° goals and the planned path, with
  Gazebo showing the arm before execution.
- **2B-after:** Gazebo showing the pose after executing the 90° goals.

Label each angle. Include RViz's current joint values in the after captures if
possible. Enter both sets of goals manually. These poses may be rejected by
collision checking: if planning fails, submit the goal values and planning-error
capture instead of the corresponding executed-pose capture. Keep collision
checking enabled and ask the TA before continuing.

**Answer:** What does Plan do, and what changes when you click Execute?

## Checkpoint 3: Edit and load blocks from JSON

Change green's starting position and hex color code as described in tutorial
section 3, save the JSON, then load the blocks.

**Submit:** Captures showing:

- The edited green block entry and its color entry in VS Code.
- The resulting three blocks in Gazebo.

You may combine these into one screenshot if both windows are readable.

**Answer:** Why does running `load` again preserve an existing block's live
position instead of moving it to an edited JSON starting position?

## Checkpoint 4: Move blocks using coordinates

Use direct `pick` commands to move red by changing X, blue by changing Y, and
green by changing both X and Y. Keep the blocks separate on the table.

**Submit:** One Gazebo screenshot after all three moves. Write the three full
`ros2 run block_skills blocks pick ...` commands below it.

**Answer:** How does changing both X and Y differ from changing only one
coordinate?

## Checkpoint 5: Add and move yellow

Add yellow through JSON, load it, then use a direct `pick` command to move it
to a clear table position.

**Submit:** One Gazebo screenshot showing yellow after the robot placement.
Keep yellow separate from the tower.

**Answer:** What do the three pairs in a `#RRGGBB` color code represent?

## Checkpoint 6: Build and rearrange towers

Build a **red–blue–green** tower, bottom to top. Then rearrange it into a
**blue–green–red** tower without resetting the scene. Calculate destination
centres and use direct `pick` commands. Do not use `move`, `randomize` or the
`stack` shortcut.

Add one additional colored block beside the rearranged tower. Choose a color
**other than red, green, blue or purple**. Choose it with an online hex color
picker and put its `#RRGGBB` code directly in the new block's `color` field.
Tutorial section 6.3 shows the format. Yellow is allowed, but you must add a
new block with a unique name; the existing checkpoint 5 block alone does not count.
Choose your own unique hex code for this submission; do not copy the tutorial's
example code or another student's code.

**Submit:**

- **6A:** A screenshot of the red–blue–green tower. Below it, list the three
  block-centre coordinates and show your height calculation.
- **6B:** A screenshot of the blue–green–red tower with your new colored block
  beside it. Write your chosen hex color code below the picture.
- **6C:** A screenshot of `src/block_skills/config/blocks.json` in VS Code
  showing the new block's complete entry, including its unique `name`, hex
  `color` code and `position`. The name must match the block shown in 6B.

Keep each tower at three cubes. Yellow and your new colored block remain
separate from the tower.

**Answer:** What move order did you use to rearrange the tower, and why must a
top block move before its support?

## Final submission

Submit your Word report containing checkpoints 1–6 and all six answers, plus
your edited `blocks.json`. Include both the final scene (6B) and JSON screenshot
(6C) so the submitted color code can be checked. If a checkpoint is unfinished, include an error
screenshot and one sentence describing what you tried.

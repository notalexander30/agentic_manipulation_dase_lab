# Tutorial media review

Restore point before this work: `backup/before-tutorial-media-20261102-084441` (`ed859d0a7aa14dd9cbe25d216ef97da940bf46ce`). This snapshot includes the
tracked changes and untracked source files present before media work. It is
local and has not been pushed. The working branch and staging area were left
unchanged when creating it.

To restore only the tutorial to that saved version, run from the project root:

```bash
git restore --source=backup/before-tutorial-media-20261102-084441 -- TUTORIAL.md
```

To inspect the complete saved project in another folder without replacing your
current files:

```bash
git worktree add ../ur10e-before-media backup/before-tutorial-media-20261102-084441
```

The isolated capture workspace is `/home/xander/ur10e-media-review`, using
Compose project `ur10e-media` and image `ur10e-media:humble`. The image build
reused cached layers and existing pinned upstream checkouts; custom packages
were built in the separate workspace. This is not a cold installation test.

## Capture results and limits

- Gazebo world, robot stage, live joint-state publisher, active controllers and
  skill action server were checked. Initial block list was empty.
- Explicit JSON loading created three blocks. Table placements of red, blue
  and green returned verified success; adding yellow preserved their live poses.
- A MoveGroup action moved shoulder pan by about 0.0998 rad. This verifies the
  execution path, **not manual RViz clicks**. RViz was opened and connected;
  its camera, font scale and window size were adjusted for readable captures.
- The first yellow pick at starting centre `(0.90, 0.30, 0.675)` failed with
  `MOTION_FAILED` / MoveIt error -2 before grasping. Planner logs reported a
  predicted table/upper-arm collision. No block was held and no fault remained.
- For recovery, yellow was repositioned as scene preparation to
  `(0.55, 0.12, 0.675)` using the existing `move` interface. Its pick to
  `(0.85, 0.30, 0.675)` then passed. The tutorial and command guide now use the
  central starting example. A fresh JSON reload spawned yellow at the updated starting position, and its
  subsequent pick passed. Collision checks were kept enabled.
- X=1.50 was rejected with `INVALID_REQUEST`. A corrected yellow placement
  passed. A separate capture request sent while that task was busy was rejected;
  its image was discarded and recaptured after the task ended.
- The first red–blue–green tower passed; repeating its final coordinate request
  returned `already_complete=true`. Picking covered blue returned `BLOCK_NOT_TOP`.
- The second blue–green–red tower and the edited blue position after a fresh
  reload were verified.
- Terminal screenshots show real interactive prompts and command output.
- The overview is real Gazebo footage of the two coordinate-based placements,
  sped up 3×. It contains no AI-generated imagery or simulated success overlays.

The current handout supplies `lab-files.zip` and no longer relies on the
incomplete GitHub download. Publishing the repository changes remains pending.

The flat sharing copy is `/home/xander/ur10e-workshop-share/TUTORIAL.md`;
its pictures, video and lab files are adjacent to it. The student copy includes
no supporting README documents.

## MoveIt movement examples

The added before/after RViz images were captured from a fresh simulation.
A plan-only MoveGroup request succeeded while shoulder pan remained unchanged.
The execution request then succeeded and shoulder pan changed by 0.10076 rad;
other joint goals bent the arm. These requests used the ROS action interface.
Manual marker dragging and button clicks remain student activities. An initial
joint-goal choice was rejected with error -27; revised joint goals planned and
executed successfully.

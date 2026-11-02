# Verification record

## Published ZIP audit — 2 November 2026

The missing `lab-files.zip` was published to GitHub main in commit 212ebad.
It was downloaded back from the public repository and matched the local ZIP.
A separate folder containing only the extracted ZIP built both custom packages
from scratch (`2 packages finished`, 57.9 seconds), using the Docker image built
from the tutorial dependencies. No separate student handout or repository clone
is needed for the custom packages. The image build reused cached dependency
layers; fresh Ubuntu tool installation and an uncached package download were
not repeated. The external repository revisions tested were robot 9645e14,
LinkAttacher b056289, and gazebo_ros2_control's humble branch 42d875b.

The GUI run exposed two wall-clock motion timeouts. One occurred before grasp;
another occurred while transporting green and reported `holding_block=true`.
The scene was reset before retrying. Gazebo was running at about 0.45 real-time
factor. Compose now caps Mesa software-rendering threads at two, and the skill
server's configurable `motion_timeout` defaults to 240 seconds instead of 90.
Cancellation and collision/placement checks remain enabled. Green and yellow
then completed their real pick, transport, release and placement checks.
A subsequent second-tower attempt was rejected with INVALID_MOTION_PLAN (-2)
because the generated path contained forearm/gripper self-collisions. No
transport was executed. This specific pre-execution rejection now uses the
existing three-attempt planning retry; controller failures remain terminal.

The clean ZIP package checks initially passed 18 tests; all 20 passed after
adding the rejected-plan versus controller-failure regression checks. An earlier run of those tests
against the actively edited workshop configuration failed two fixture
assumptions (three initial blocks and a new yellow name). Rerunning against
the unedited extracted configuration passed all 18; the student's edited scene
was not used as the test fixture for the final result.

Both all-six-joint targets (45 degrees and 90 degrees) were submitted to MoveIt
as plan-only goals and returned error -27, with no execution. This does not
verify manual RViz clicks or those executed poses. The tutorial already permits
capturing the rejected goal/error instead of executing an invalid plan.

The final uninterrupted tower challenge passed after recovery:

| Operation | Verified task ID |
| --- | --- |
| Blue on red | 56c9249b228a42acbea8ddae9ca03e9d |
| Green on blue | 1a243861469c430b868fc48814f8d2cd |
| Unstack green to table | e8fd64b4f6874da3928dce697f1d69b6 |
| Move blue to new base | 7cf902be9152463083391071bda477ec |
| Green on new blue base | 17e5560938024e98aecec5a16914e197 |
| Red on green | 87bc9457fb6b4fe6a7753ced78af4c63 |

There was no scene reset between these six operations. Green transport retried
both rejected plans and succeeded on its third attempt. The final red centre
was approximately `(0.699993, -0.050012, 0.774678)` m. A new `student_teal`
block with literal color `#00B8D4` loaded beside the tower, with yellow still
separate. Repeating the final coordinate request returned verified success and
`already_complete=true`, task d8519b4ee94d4aa4950801f961da79e0. Its saved
Gazebo screenshot was opened to inspect the completed scene. Earlier, moving
a covered blue block returned `BLOCK_NOT_TOP` before motion. All tutorial
image paths resolve locally. The tutorial itself was left unchanged.

Runtime logs, results and screenshots are retained locally under
`/home/xander/ur10e-github-audit/audit-results` and its `artifacts` directory.
The user's other idle simulation was paused during this resource-intensive test;
its scene was preserved.

## Latest-branch workshop test — 2 November 2026

The latest IFRA default branches matched commits 9645e14 and b056289. The
latest gazebo_ros2_control default branch (3e6d3f4, version 0.7.6) failed to
compile against Humble APIs. Its latest humble branch, 42d875b, built successfully.
Startup initially failed parsing XML comments in the robot-description parameter.
The custom launcher now removes comments from the generated URDF; the upstream
repositories remain unmodified. Controllers then started and JSON loading passed.

The new student Python client placed blue on red successfully. Green transport
at the first tower location failed with MOTION_FAILED while held; the reported
fault required a scene restart. After restarting with a clear tower location,
blue-on-red and green-on-blue both returned verified success with screenshot
evidence. The final task ID was b901008ebf51408785f67942d138a806. This validates
the tested configuration and recovery path, not every coordinate or future
branch update. Earlier tutorial images/video remain examples from prior runs.
Logs and reports are retained in /home/xander/ur10e-latest-test.


## Coordinate-based towers — 2 November 2026

The workshop now uses explicit destination centres through `pick`, with no
support-name shortcut. The server validates the real support beneath an
elevated target while preserving the supplied coordinates. All 13 tests passed
with no errors, failures or skips, including invalid support, non-finite target,
cyclic support and excessive tower-height cases.

In Gazebo, blue placement at `(0.55, -0.28, 0.725)` and green placement at
`(0.55, -0.28, 0.775)` both returned verified success and screenshot evidence.
The green task was `5fb25294291143709068678eb2179d59`; its measured centre was
`(0.549990, -0.280001, 0.774680)`. The screenshot was opened and showed the tower.
Repeating the coordinate request returned `already_complete=true`. Moving the
covered blue block returned `BLOCK_NOT_TOP`; an elevated destination with no
support returned `INVALID_REQUEST`, both before motion.

An initial screenshot attempt failed because this workspace lacked the desktop
authorization file. After supplying valid Xauthority and restarting the test
scene, screenshot capture and the above tasks succeeded. Logs are retained in
`/tmp/ur10e-coordinate-audit` and may be cleared; task reports/screenshots are
generated under the local `artifacts/` directory. These tests ran on the current
Docker desktop setup, not a second computer.

## Staged launch and JSON loading — 2 November 2026

The revised custom packages were built and exercised in a separate Compose
workspace using the installed `ur10e:humble` image. All 12 package tests passed
with no errors, failures or skipped tests.

- `world.launch.py` exposed a live table through Gazebo's state service, with
  no robot or blocks. `robot.launch.py` then loaded the arm, gripper, controllers,
  MoveIt and RViz; the ready server initially returned an empty block list.
- `load` spawned the three JSON blocks with the edited green position and
  color. Repeating it spawned zero models. Appending a yellow definition added
  one block while preserving the red block's current, moved position.
- A batch containing a valid candidate followed by a candidate overlapping
  the live red block was rejected before either candidate spawned.
- Physical red placement at `(0.82, -0.28, 0.675)`, blue-on-red and green-on-blue
  all returned verified success with screenshot evidence. The final screenshot
  was opened and showed the three-block tower and separate yellow block.
- Repeating the top stacking task returned `already_complete=true`; reloading
  JSON preserved all four live blocks and the tower.
- After stopping both stages, the original `sim.launch.py` reported ready and
  automatically loaded all four configured blocks at their starting positions.

The final stacking task was `230861b4f85f4146b0b7023924e1b786`, with measured
green centre `(0.819955, -0.279993, 0.774678)`. Logs, results and screenshots
are in `/tmp/ur10e-stages.GVfp5A` on this computer and may be cleared. This audit
used the local revised source; the new public download path requires publishing
the source and documentation together. It does not establish compatibility
with a second computer or a cold Docker build.

## Fresh workspace audit of the revised tutorial

An additional audit started in an empty temporary directory, downloaded the
three public repositories at the tutorial's pinned commits, and downloaded
the custom source/Docker files from published revision `94c5cab`. No existing
host `upstream/`, custom build or installation was copied into that workspace.
The launcher was created from the code supplied in the revised tutorial.

- Docker build passed using matching cached layers, producing image ID
  `9c6003db9e00716790cd4405414b35ea95f3e0ac090db74adb67a3158ce1134e`.
- Both custom packages built from scratch in the empty workspace.
- GUI launch reported ready, and live poses matched the starting scene.
- Restart loaded the edited green position (`x=0.65`) and `approach_height=0.20`.
- The tutorial's placement script succeeded at `(0.82, -0.28, 0.675)` and,
  after changing its offsets, `(0.85, -0.35, 0.675)`.
- Blue-on-red and green-on-blue returned `success=true`, `verified=true`,
  and screenshot evidence. The screenshots were opened and inspected.
- Repeating green-on-blue returned `already_complete=true` without motion.

The final three-block task ID was `6708f6bf01674e0388747432b81a66e0`;
its measured top-block centre was approximately `(0.849961, -0.350020, 0.774678)`.
Audit logs and reports are in `/tmp/ur10e-fresh.BGLE3i` on the test computer;
this temporary directory is not a dependency of the tutorial or distributed
evidence. It may be cleared by the operating system.

This verifies the revised download/build/run path on the existing Linux
desktop. It does not verify installing Docker on a second computer, a cold
uncached apt build, ARM, or another graphics environment. Ubuntu package
patch versions are still resolved at build time.

## Original verification record

This document records tests completed on 22 October 2026. It is historical
evidence, not a claim that every future build or computer will produce the same
result. Run the commands in [instructor setup](INSTRUCTOR_SETUP.md#tests) on the target
computer before reporting that its simulation works.

Raw colcon output, temporary logs, build trees and task artifact folders are
generated data and are not distributed with the clean source repository. The
two retained images are representative evidence from verified runs:

- [scene.png](scene.png): UR10e, table and spaced colored blocks.
- [stack.png](stack.png): verified red–blue–green stack.

## Tested environment

| Component | Tested value |
| --- | --- |
| Host | Ubuntu 26.04.1, Linux x86_64 |
| Host ROS | Lyrical installed but unused |
| Container | Ubuntu 22.04.5, ROS 2 Humble |
| Gazebo | Gazebo Classic 11.10.2 |
| MoveIt | MoveIt 2.5.10 |
| Graphics | XWayland with Mesa software rendering |
| Robot | Original IFRA UR10e and Robotiq 2F-85 |
| Grasp simulation | IFRA_LinkAttacher |

The base-image digest is pinned in `docker/Dockerfile`; source revisions are
listed in `repositories.json`. Apt patch versions are resolved when the image
is built.

## Verified results

| Check | Recorded result |
| --- | --- |
| Pinned upstream build | Seven selected upstream packages compiled |
| Custom package tests | Nine passed with no failures or skips |
| Controller startup | Joint-state broadcaster, arm controller and six gripper controllers active |
| Gazebo pose lookup | Current red, blue and green poses retrieved |
| Invalid input | Unknown blocks, invalid frames and out-of-bounds targets rejected before motion |
| Red pick/place | Physical grasp, lift, transport, release, retreat and pose verification passed |
| Extra blocks | Red and yellow blocks spawned and returned by the service |
| Ambiguous color/occupied target | Rejected with machine-readable error codes |
| External repositioning | Skill used a blue block pose changed through Gazebo state service |
| Changed yaw | Blue placed and verified at yaw 0.35 rad |
| Collision obstacle | Approach planning failed without attaching the block |
| Concurrent requests | Second skill and scene mutation rejected while busy |
| Cancellation during planning | Canceled cleanly without holding a block |
| Cancellation after attachment | Held state and recovery fault reported; restart recovered |
| Randomization | A seed reproduced positions and required spacing |
| Randomized pick/place | Green was picked from a randomized pose and placed at a new yaw |
| Two-block stack | Blue placed on red and repeatedly verified |
| Three-block stack | Green placed on blue while all supports remained stable |
| Idempotent stack request | Returned `already_complete=true` without robot motion |
| Stack height | Fourth block rejected with `STACK_LIMIT` |
| Support protection | Removing a supporting block rejected with `BLOCK_NOT_TOP` |
| Screenshot evidence | Visible Gazebo window captured and matched a durable JSON report |
| Missing display | Returned `EVIDENCE_UNAVAILABLE` without claiming success |

## Measured examples

Positions are block centres in metres in the Gazebo `world` frame.

| Case | Requested position | Measured final position |
| --- | --- | --- |
| Red pick/place | `(0.82, -0.28, 0.675)` | `(0.819976, -0.280015, 0.675000)` |
| Green after randomization | `(0.45, -0.40, 0.675)` | `(0.449996, -0.399982, 0.674991)` |
| GUI demo red | `(0.85, -0.35, 0.675)` | `(0.849972, -0.349958, 0.675000)` |
| GUI demo blue | `(0.85, 0.00, 0.675)` | `(0.849971, 0.000014, 0.675000)` |
| GUI demo green | `(0.85, 0.35, 0.675)` | `(0.849990, 0.349997, 0.675000)` |
| Top of verified three-block stack | Derived from supports | `(0.549962, -0.279986, 0.774678)` |

The stack task used eleven pose/orientation/velocity samples, including a
second physical check after screenshot capture. The first development attempt
tipped after release and correctly returned failure. Contact stiffness,
damping, correction velocity, contact points and solver iterations were then
tuned, and later two- and three-block tests passed at the 5 mm stack tolerance.

## Manual RViz diagnosis

On 22 October 2026, all controllers were active, Gazebo was unpaused and RViz
was connected to `ur10e_arm`. A collision-aware `/move_action` goal offset the
shoulder-pan joint by 0.1 rad. MoveIt returned success with eight trajectory
points, while `/joint_states` changed from 0.00000428 to 0.10038280 rad.

This verified the controller and MoveIt execution path. The launch was updated
to show the query-goal preview, use a translucent collision scene and expose
the Displays panel. Manual RViz clicks still require a goal different from the
current state before Plan and Execute can produce visible motion.

## Resolved implementation issues

- Renamed a service-client dictionary that collided with names reserved by
  `rclpy.Node`.
- Removed a redundant world-object removal during MoveIt attachment.
- Dispatched six gripper commands together to keep the parallel linkage
  aligned and avoid pushing the block.
- Used the measured block-to-gripper transform during transport.
- Added bounded retries when OMPL produced no trajectory; execution failures
  are reported without replaying motion.
- Added low-velocity settling checks before physical detachment.

## Limits of the verification

The native Ubuntu workflow, hardware GPU acceleration and a physical UR10e
were not tested. The supported objects are upright, uniformly sized cubes on
the configured table. The scene is refreshed before each movement; it is not a
dynamic-obstacle avoidance system. The configured stack limit is three aligned
cubes. Tilted, overhanging or taller stacks remain outside the tested scope.

Gazebo uses a simulated attachment joint, so this is not a friction-only grasp
test. Table placement tolerance is 0.02 m, stack placement tolerance is 0.005 m
and yaw tolerance is 0.15 rad. Success at the recorded poses does not guarantee
that every coordinate in the bounding workspace is kinematically reachable or
collision-free.

Expected upstream messages include the missing optional recognition action,
the absence of an Octomap sensor plugin, unrealistic visualized gripper-knuckle
inertias, and the TCP marker's missing collision geometry. These did not block
the verified tasks. Planning, controller, attachment, stale-state and evidence
errors remain actionable failures.

# Robot registry

| Robot | Role | Base URL | Discovery |
| --- | --- | --- | --- |
| ur10e_sim | Colored-block manipulation in Gazebo | `UR10E_SIM_BASE_URL` (default `http://127.0.0.1:8880`) | `/code/sdk` |

ROS endpoints behind the adapter are `/skills/status`, `/blocks` and
`/skills/pick_place`. Their planning, gripper, verification and reporting remain
owned by the existing `block_skills` server in the `ur10e` Docker container.

Use the `ur10e-sim` workspace skill. Authentication comes from
`UR10E_SIM_API_TOKEN`, loaded by the project wrapper from `.container/agent-token`.
Do not read or print the token. The wrapper does not start, reset, or move Gazebo.

Default mode is headless, with state verification and `evidence:"none"`.
Screenshots require a separately working GUI setup and an explicit request.
Fixed staging defaults to the three startup block locations. Additional blocks
can exhaust free sites; report REARRANGEMENT_UNAVAILABLE rather than inventing
new staging coordinates.

# UR10e simulation fleet entry

Merge this entry into the active ABot-Claw workspace's `ROBOT.md`.

| Robot | Base URL | Guide | SDK |
| --- | --- | --- | --- |
| ur10e_sim | `http://127.0.0.1:8880` | `/docs/guide/html` | `/code/sdk/markdown` |

Set `UR10E_SIM_BASE_URL` to the reachable adapter URL and `UR10E_SIM_API_TOKEN`
to the shared Bearer token in the OpenClaw process environment. All routes require
the token. Discovery routes return JSON with the available operations.

Route colored-block requests explicitly targeting the UR10e/Gazebo simulation
to the `ur10e-sim` skill. If the active `MISSION.md` or generic run-robot-task
skill enumerates only Piper/G1/Go2, extend that selection to include `ur10e_sim`.
No physical driver, CAN interface, camera, arbitrary-code execution or remote
motion SDK is part of this robot. Preserve the other fleet routes.

Use `stack_order` to dismantle obstructing towers and build the requested RGB
order. Use `dismantle` for standalone tower removal. To cancel, read
`get_status.active_request_id`, call `cancel` with that ID, and await the original
action result; a cancellation acknowledgement does not confirm a stop.

Recovery: stop the current plan on failure. If a block remains held, restart the
simulation and adapter. If execution state is uncertain, inspect ROS status,
logs and durable task artifacts before restarting the adapter. Never use an
adapter restart as proof that the previous action stopped.

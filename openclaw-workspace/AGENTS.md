# ABot-Claw UR10e simulation workspace

At the start of each session, read `MISSION.md`, `ROBOT.md`, and `TOOLS.md`.
For block operations, read `skills/ur10e-sim/SKILL.md` and use its Python client.

This workspace operates the Gazebo UR10e through the typed HTTP adapter. Select
`ur10e_sim` for the user's robot requests here. The original ABot-Claw fleet
decision/skill/discovery pattern is retained; physical Piper/G1/Go2 routes are
not configured in this project-local workspace.

Natural-language orders mean bottom to top. Inspect live inventory, resolve
unique colors or exact names, and use the existing tools. Keep coordinates out
of user requests unless the user explicitly chooses coordinate placement.
Never replace a robot operation with invented outcomes, simulated tool output,
Gazebo teleportation, shell ROS motion commands, or generated controller code.

Invoke each manipulation once and follow its tracked process to the final
response. Do not repeat a command because a process tool returned a running
session. On cancellation use the adapter cancel tool and await the original
result. Failures stop the plan. Report task IDs and verified outcomes; distinguish
cancel acknowledgement, action acceptance, creation, and verified placement.

Do not expose credentials in replies, commands printed for the user, or logs.
Environment variables provide adapter authentication to the client. Use the
client rather than inspecting or echoing its token.

Do not perform robot actions from heartbeat checks or without a user request.

# UR10e Lab: Pick, Place and Stack

Follow [TUTORIAL.md](TUTORIAL.md) for setup, manual MoveIt joint checkpoints,
JSON blocks, direct ROS pick/place commands, and tower tasks.
Use [QUESTIONS.md](QUESTIONS.md) for submission captures and answers.

Download [lab-files.zip](lab-files.zip) for the tutorial's workspace setup.
For agent integration, start with [ABot-Claw integration notes](docs/ABOTCLAW_INTEGRATION.md);
the ROS interfaces are in `src/block_interfaces` and skill server in
`src/block_skills/block_skills/server.py`.

This branch also includes the HTTP adapter and UR10e OpenClaw skill. See
[UR10e agent setup](docs/UR10E_AGENT.md) for the adapter and
[project-local OpenClaw setup](docs/OPENCLAW_LOCAL.md) for the dedicated agent
workspace. The merged staged-launch and agent workflow needs live acceptance
testing; earlier integration results do not validate this combined revision.

Supporting documents:

- [Step-by-step personal command guide](README_COMMANDS.md)
- [Instructor setup](docs/INSTRUCTOR_SETUP.md)
- [Verification record](docs/verification.md)
- [ABot-Claw integration notes](docs/ABOTCLAW_INTEGRATION.md)
- [UR10e adapter setup](docs/UR10E_AGENT.md)
- [Project-local OpenClaw setup](docs/OPENCLAW_LOCAL.md)

- [Screenshot/video review and restore point](docs/MEDIA_REVIEW.md)

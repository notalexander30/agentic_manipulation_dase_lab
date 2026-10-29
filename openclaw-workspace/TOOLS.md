# Robot tools

From this workspace the client is:

```bash
python3 skills/ur10e-sim/scripts/ur10e_sim.py get_status
python3 skills/ur10e-sim/scripts/ur10e_sim.py list_blocks
python3 skills/ur10e-sim/scripts/ur10e_sim.py stack '{"block":"blue","support":"red","evidence":"none"}'
python3 skills/ur10e-sim/scripts/ur10e_sim.py stack_order '{"order":"GBR","evidence":"none"}'
python3 skills/ur10e-sim/scripts/ur10e_sim.py dismantle '{"block":"blue","evidence":"none"}'
```

These are usage examples, not startup actions. Execute only the requested task.
Read `skills/ur10e-sim/SKILL.md` for all arguments and result interpretation.

The project wrapper loads the token and local OpenClaw paths. Use read/exec/
process tools to invoke the client once and follow running execution sessions.
To stop a plan, get the active request ID and call the adapter's `cancel` tool.
Killing a client process or canceling an LLM turn does not confirm that ROS stopped.

Project docs live one directory above this workspace, in `../docs/`.

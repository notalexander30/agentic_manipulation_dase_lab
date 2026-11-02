# Local command reference

The complete student workflow and direct ROS commands are in
[TUTORIAL.md](TUTORIAL.md). Submission requirements are in
[QUESTIONS.md](QUESTIONS.md). Students do not create Python or shell scripts.

For this existing workspace, open an Ubuntu desktop terminal:

```bash
cd "/home/xander/abotclaw+piper" # Replace xander if using a different Linux account; use your actual project folder.
code .
export LAB_UID=$(id -u) LAB_GID=$(id -g)
umask 077
touch .xauth
xauth nlist "$DISPLAY" | sed 's/^..../ffff/' | xauth -f .xauth nmerge -
docker compose run --rm lab
```

Inside Docker:

```bash
colcon build --base-paths src --symlink-install --parallel-workers 2
source /work/install/setup.bash
```

Continue from tutorial section 2. Reuse the existing image and repositories;
repeat the image build only after changing its dependencies or upstream sources.

"""JSON loading must respect live objects and avoid partial invalid batches."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip('rclpy')
pytest.importorskip('block_interfaces.msg')
from block_interfaces.msg import Block
from geometry_msgs.msg import PoseStamped
from block_skills.server import Server, pose_at


@pytest.fixture
def loader(tmp_path):
    config = json.loads((Path(__file__).parents[1] / 'config' / 'blocks.json').read_text())
    path = tmp_path / 'blocks.json'
    path.write_text(json.dumps(config))
    live = [Block(name=b['name'], color=b['color'], size=config['block_size'],
                  pose=PoseStamped(pose=pose_at(b['position']))) for b in config['blocks']]
    calls = []
    fake = SimpleNamespace(config=copy.deepcopy(config), config_path=str(path),
                           registry={b.name: b.color for b in live}, block_list=lambda: live)

    def spawn(name, color, pose):
        calls.append(name)
        fake.registry[name] = color
        live.append(Block(name=name, color=color, size=config['block_size'], pose=PoseStamped(pose=pose)))

    fake.spawn = spawn
    return fake, config, path, live, calls


def test_load_adds_new_names_without_resetting_live_poses(loader):
    fake, config, path, live, calls = loader
    live[0].pose.pose.position.x = .85
    config['blocks'].append({'name': 'yellow_extra', 'color': 'yellow', 'position': [.90, .30, .675]})
    path.write_text(json.dumps(config))
    assert Server.load_blocks(fake) == 1
    assert calls == ['yellow_extra']
    assert live[0].pose.pose.position.x == .85
    assert Server.load_blocks(fake) == 0
    assert calls == ['yellow_extra']


def test_load_checks_whole_batch_against_live_positions_before_spawning(loader):
    fake, config, path, live, calls = loader
    live[0].pose.pose.position.x, live[0].pose.pose.position.y = .85, .30
    config['blocks'].extend([
        {'name': 'yellow_free', 'color': 'yellow', 'position': [.90, -.30, .675]},
        {'name': 'yellow_occupied', 'color': 'yellow', 'position': [.90, .30, .675]},
    ])
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match='too close'):
        Server.load_blocks(fake)
    assert calls == []
    assert len(fake.registry) == 3


def test_load_rejects_world_changes_that_require_a_scene_restart(loader):
    fake, config, path, _, calls = loader
    config['table']['size'][0] += .1
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match='restart world and robot'):
        Server.load_blocks(fake)
    assert calls == []

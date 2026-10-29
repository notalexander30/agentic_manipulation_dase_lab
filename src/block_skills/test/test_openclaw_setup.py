"""Verify local setup preserves credentials/config and keeps state out of Git."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


class OpenClawSetupTests(unittest.TestCase):
    def setUp(self):
        script = Path(__file__).resolve().parents[3]/'scripts/setup_openclaw.py'
        spec = importlib.util.spec_from_file_location('local_setup', script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.configure = module.configure
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        skill = self.root/'openclaw-workspace/skills/ur10e-sim/SKILL.md'
        skill.parent.mkdir(parents=True)
        skill.write_text('test skill', encoding='utf-8')

    def test_local_paths_timeouts_and_git_exclusions(self):
        path = self.configure(self.root)
        config = json.loads(path.read_text())
        self.assertEqual(path.parent, self.root/'.openclaw-state')
        self.assertEqual(config['agents']['defaults']['workspace'], str(self.root/'openclaw-workspace'))
        self.assertEqual(config['tools']['exec']['timeoutSeconds'], 3450)
        self.assertEqual(config['gateway']['bind'], 'loopback')
        self.assertTrue(config['skills']['entries']['ur10e-sim']['enabled'])
        ignored = (self.root/'.gitignore').read_text().splitlines()
        self.assertIn('.openclaw-runtime/', ignored)
        self.assertIn('.openclaw-state/', ignored)
        self.assertNotIn('UR10E_SIM_API_TOKEN', path.read_text())

    def test_rerun_preserves_auth_model_and_operator_policies(self):
        path = self.configure(self.root)
        config = json.loads(path.read_text())
        original_token = config['gateway']['auth']['token']
        config['agents']['defaults']['model'] = {'primary': 'test/provider-model'}
        config['tools']['exec']['mode'] = 'ask'
        config['tools']['exec']['timeoutSeconds'] = 4000
        path.write_text(json.dumps(config), encoding='utf-8')
        ignored_before = (self.root/'.gitignore').read_text()
        self.configure(self.root)
        updated = json.loads(path.read_text())
        self.assertEqual(updated['gateway']['auth']['token'], original_token)
        self.assertEqual(updated['agents']['defaults']['model'], config['agents']['defaults']['model'])
        self.assertEqual(updated['tools']['exec']['mode'], 'ask')
        self.assertEqual(updated['tools']['exec']['timeoutSeconds'], 4000)
        self.assertEqual((self.root/'.gitignore').read_text(), ignored_before)

    def test_missing_workspace_does_not_create_credentials(self):
        missing = self.root/'other'
        with self.assertRaises(ValueError):
            self.configure(missing)
        self.assertFalse((missing/'.openclaw-state').exists())


if __name__ == '__main__':
    unittest.main()

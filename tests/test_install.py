import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('panel_installer', Path(__file__).resolve().parents[1] / 'system/install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallTests(unittest.TestCase):
    def setUp(self):
        # Model protected system directories regardless of the login shell mask.
        previous_umask = os.umask(0o022)
        self.addCleanup(os.umask, previous_umask)
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'root'; self.root.mkdir()
        self.calls = []
        self.artifacts = installer.render('panel', '/home/panel/pi500-oled-panel',
                                          {'keys': True}, 'lightdm.service')

    def run_command(self, args):
        self.calls.append(args)
        return ''

    def install(self):
        installer.install(self.root, self.artifacts, {'default_target': 'graphical.target',
                            'display_manager': 'lightdm.service'}, self.run_command,
                            owner=(os.getuid(), os.getgid()))

    def test_install_uninstall_restores_fixture_and_keeps_unrelated_files(self):
        unrelated = self.root / 'etc/systemd/system/lightdm.service.d/other.conf'
        unrelated.parent.mkdir(parents=True); unrelated.write_text('[Service]\nNice=1\n')
        before = unrelated.stat()
        self.install()
        manifest = json.loads((self.root / installer.BACKUP / 'manifest.json').read_text())
        self.assertEqual(manifest['original']['default_target'], 'graphical.target')
        self.assertTrue(all(item['previous'] is None for item in manifest['files']))
        link = self.root / 'etc/systemd/system/multi-user.target.wants/oled-panel.service'
        self.assertTrue(link.is_symlink())
        (self.root / 'etc/oled-panel/default').write_text('headless\n')
        installer.uninstall(self.root, self.run_command)
        self.assertEqual(unrelated.read_text(), '[Service]\nNice=1\n')
        self.assertEqual(unrelated.stat().st_mode, before.st_mode)
        self.assertFalse(link.is_symlink())
        self.assertFalse((self.root / 'etc/oled-panel').exists())
        self.assertTrue((self.root / installer.BACKUP / 'manifest.json').exists())
        self.assertFalse(any('start' in command or 'set-default' in command or 'stop' in command for command in self.calls))

    def test_refuses_unmanaged_conflict_without_writing_any_install_files(self):
        conflict = self.root / 'etc/systemd/system/oled-panel.service'
        conflict.parent.mkdir(parents=True); conflict.write_text('mine')
        with self.assertRaises(FileExistsError): self.install()
        self.assertEqual(conflict.read_text(), 'mine')
        self.assertFalse((self.root / 'etc/oled-panel').exists())

    def test_failed_reload_rolls_back_every_write_and_keeps_recovery_manifest(self):
        def fail(command): raise RuntimeError('daemon-reload failed')
        with self.assertRaises(RuntimeError):
            installer.install(self.root, self.artifacts, {}, fail, owner=(os.getuid(), os.getgid()))
        self.assertFalse((self.root / 'etc/oled-panel').exists())
        self.assertFalse((self.root / 'etc/systemd/system/oled-panel.service').exists())
        manifest = json.loads((self.root / installer.BACKUP / 'manifest.json').read_text())
        self.assertEqual(manifest['state'], 'rolled-back')

    def test_uninstaller_refuses_changed_unit_before_removing_anything(self):
        self.install()
        unit = self.root / 'etc/systemd/system/oled-panel.service'; unit.write_text('new owner')
        with self.assertRaises(RuntimeError): installer.uninstall(self.root, self.run_command)
        self.assertEqual(unit.read_text(), 'new owner')
        self.assertTrue((self.root / 'etc/oled-panel/actions.json').exists())

    def test_symlink_parent_does_not_escape_fixture(self):
        external = Path(self.temp.name) / 'external'; external.mkdir()
        (self.root / 'etc').symlink_to(external)
        with self.assertRaises((PermissionError, OSError)): self.install()
        self.assertEqual(list(external.iterdir()), [])

    def test_interrupted_preparing_manifest_never_deletes_unproven_files(self):
        backup = self.root / installer.BACKUP; backup.mkdir(parents=True)
        path = self.root / 'etc/systemd/system/oled-panel.service'
        path.parent.mkdir(parents=True); path.write_text('unrelated later file')
        manifest = {'state': 'preparing', 'files': [{'path': 'etc/systemd/system/oled-panel.service',
                    'previous': None}], 'created_dirs': []}
        (backup / 'manifest.json').write_text(json.dumps(manifest))
        with self.assertRaisesRegex(RuntimeError, 'incomplete.*inspect'):
            installer.uninstall(self.root, self.run_command)
        self.assertEqual(path.read_text(), 'unrelated later file')
        self.assertFalse(self.calls)

    def test_stage_outputs_exact_artifacts_without_activation(self):
        stage = Path(self.temp.name) / 'stage'
        installer.stage(self.artifacts, stage)
        for relative, item in self.artifacts.items():
            path = stage / relative
            if item.get('link'):
                self.assertEqual(os.readlink(path), item['link'])
            else:
                self.assertEqual(path.read_bytes(), item['data'])
                self.assertEqual(path.stat().st_mode & 0o777, item['mode'])
        self.assertEqual(self.calls, [])

    def test_render_rejects_argument_injection(self):
        for user, project, manager in [('panel ALL=(ALL)', '/home/panel/panel', 'lightdm.service'),
                                       ('panel', '/home/panel/panel\nExecStart=bad', 'lightdm.service'),
                                       ('panel', '/home/panel/panel', '../ssh.service')]:
            with self.assertRaises(ValueError): installer.render(user, project, {}, manager)

    def test_selector_finishes_headless_splash_before_startup_is_released(self):
        unit = self.artifacts['etc/systemd/system/oled-panel-selector.service']['data'].decode()
        self.assertIn('ExecStartPost=+/usr/bin/python3 -I /usr/local/libexec/oled-panel-action selector-finish', unit)
        self.assertIn('ExecStopPost=+/usr/bin/python3 -I /usr/local/libexec/oled-panel-action selector-cleanup', unit)
        sudoers = self.artifacts['etc/sudoers.d/oled-panel']['data'].decode()
        self.assertNotIn('selector-finish', sudoers)


if __name__ == '__main__': unittest.main()

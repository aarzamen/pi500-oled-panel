import importlib.util
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

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

    def test_integration_is_explicit_and_keeps_desktop_saved_default(self):
        for enabled in (False, True):
            artifacts = installer.render('panel', '/home/panel/pi500-oled-panel',
                                         {'keys': True, 'panelbridge': enabled, 'boot_default': 'Headless'}, 'lightdm.service')
            device = json.loads(artifacts['etc/oled-panel/device.json']['data'])
            actions = json.loads(artifacts['etc/oled-panel/actions.json']['data'])
            self.assertIs(device['panelbridge'], enabled)
            self.assertIs(actions['panelbridge'], enabled)
            self.assertEqual(device['boot_default'], 'Desktop')
            self.assertEqual(artifacts['etc/oled-panel/default']['data'], b'desktop\n')
            sudoers = artifacts['etc/sudoers.d/oled-panel']['data'].decode()
            self.assertEqual('set-default wireless' in sudoers, enabled)
            self.assertNotIn('selector-reset', sudoers)
            unit = artifacts['etc/systemd/system/lightdm.service.d/60-oled-panel.conf']['data']
            self.assertEqual(unit, self.artifacts['etc/systemd/system/lightdm.service.d/60-oled-panel.conf']['data'])

    def test_render_rejects_nonboolean_enrollment(self):
        for enabled in (1, 'true', None, []):
            with self.subTest(enabled=enabled), self.assertRaises(ValueError):
                installer.render('panel', '/home/panel/panel', {'panelbridge': enabled}, 'lightdm.service')

    def test_cli_flag_enables_only_the_staged_integration_configuration(self):
        stage = Path(self.temp.name) / 'enabled-stage'
        supplied = {'keys': True, 'panelbridge': False}
        with patch.object(installer, 'preflight', return_value=(supplied, 'lightdm.service', {})):
            installer.main(['--user', 'panel', '--project', '/home/panel/panel', '--config', '/fixture/config.json',
                            '--render-only', str(stage), '--panelbridge'])
        self.assertIs(json.loads((stage / 'etc/oled-panel/device.json').read_text())['panelbridge'], True)
        self.assertEqual((stage / 'etc/oled-panel/default').read_text(), 'desktop\n')
        self.assertEqual(self.calls, [])

    def test_integrated_uninstall_manifest_preserves_unrelated_files_and_removes_choices(self):
        self.artifacts = installer.render('panel', '/home/panel/pi500-oled-panel',
                                          {'keys': True, 'panelbridge': True}, 'lightdm.service')
        self.install()
        runtime = self.root / 'run/oled-panel'; runtime.mkdir(parents=True)
        (runtime / 'choice.json').write_text('{"mode":"wireless","panelbridge":true}')
        (runtime / 'headless').write_text('stale')
        (runtime / 'unrelated').write_text('preserve')
        (self.root / 'etc/oled-panel/default').write_text('wireless\n')
        manifest_path = self.root / installer.BACKUP / 'manifest.json'
        manifest = json.loads(manifest_path.read_text())
        self.assertEqual({item['path'] for item in manifest['files']}, set(self.artifacts))
        installer.uninstall(self.root, self.run_command)
        self.assertFalse((runtime / 'choice.json').exists())
        self.assertFalse((runtime / 'headless').exists())
        self.assertEqual((runtime / 'unrelated').read_text(), 'preserve')
        self.assertEqual(json.loads(manifest_path.read_text())['state'], 'uninstalled')

    def test_integrated_device_configuration_edits_still_block_uninstall(self):
        self.artifacts = installer.render('panel', '/home/panel/pi500-oled-panel',
                                          {'keys': True, 'panelbridge': True}, 'lightdm.service')
        self.install()
        device = self.root / 'etc/oled-panel/device.json'
        device.write_text('{"panelbridge":false}')
        with self.assertRaises(RuntimeError): installer.uninstall(self.root, self.run_command)
        self.assertTrue((self.root / 'etc/systemd/system/oled-panel.service').exists())
        self.assertEqual(device.read_text(), '{"panelbridge":false}')

    def test_pi5_is_not_implicitly_accepted_for_gpio_integration(self):
        with patch.object(installer.Path, 'read_text', return_value='Raspberry Pi 5 Model B Rev 1.0\0'):
            with self.assertRaisesRegex(RuntimeError, 'expected verified Pi 500'):
                installer.preflight(type('Args', (), {'panelbridge': True})())


class PanelBridgeEnrollmentTests(unittest.TestCase):
    """Exercise real preflight and file reads against a synthetic system root."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / 'system-root'; self.root.mkdir(mode=0o755)
        self.project = self.root / 'project'; self.project.mkdir()
        python = self.project / '.venv/bin/python'; python.parent.mkdir(parents=True)
        python.write_text('fixture only'); python.chmod(0o755)
        self.config = self.project / 'device.json'
        self.config.write_text('{"keys":true,"panelbridge":true}')
        self.enrollment = self.root / 'etc/panelbridge/enrollment.json'
        self.enrollment.parent.mkdir(parents=True)
        self.enrollment.write_text('{"api_version":1,"normal_uid":1000,"rescue_uid":null}')
        self.enrollment.chmod(0o644)
        self.capability = self.root / 'usr/share/panelbridge/oled-integration.json'
        self.capability.parent.mkdir(parents=True)
        self.capability.write_text('{"api_version":1,"startup_choice":1,"session_bus":"org.panelbridge.Session1"}')
        self.capability.chmod(0o644)
        self.manager = self.root / 'lightdm.service'; self.manager.write_text('[Service]\n')
        self.args = SimpleNamespace(user='panel', project=str(self.project), config=str(self.config), panelbridge=False)
        self.foreign_inode = None
        self.opens, self.commands = [], []
        original_open, original_fstat = os.open, os.fstat
        original_read_text, original_resolve, original_readlink = Path.read_text, Path.resolve, os.readlink
        def open_file(path, flags, *args, **kwargs):
            self.opens.append((str(path), flags))
            return original_open(self.root if str(path) == '/' else path, flags, *args, **kwargs)
        def metadata(fd):
            info = original_fstat(fd)
            return SimpleNamespace(st_uid=1001 if info.st_ino == self.foreign_inode else 0,
                                   st_mode=info.st_mode, st_nlink=info.st_nlink)
        def read_text(path, *args, **kwargs):
            if str(path) == '/proc/device-tree/model': return 'Raspberry Pi 500 Rev 1.0\0'
            return original_read_text(path, *args, **kwargs)
        def resolve(path, *args, **kwargs):
            if str(path) == '/etc/systemd/system/display-manager.service': return self.manager
            return original_resolve(path, *args, **kwargs)
        def readlink(path, *args, **kwargs):
            if str(path) == '/etc/systemd/system/display-manager.service': return '/usr/lib/systemd/system/lightdm.service'
            return original_readlink(path, *args, **kwargs)
        def run(command, **kwargs):
            self.commands.append(command)
            return 'graphical.target' if command == ['/usr/bin/systemctl', 'get-default'] else ''
        replacements = [(installer.os, 'open', open_file), (installer.os, 'fstat', metadata),
                        (installer.os, 'geteuid', lambda: 0), (installer.os, 'readlink', readlink),
                        (installer.Path, 'read_text', read_text), (installer.Path, 'resolve', resolve),
                        (installer.pwd, 'getpwnam', lambda user: SimpleNamespace(pw_uid=1000)),
                        (installer, 'run', run)]
        for target, name, value in replacements:
            replacement = patch.object(target, name, value)
            replacement.start(); self.addCleanup(replacement.stop)

    def test_matching_account_accepts_enrollment_without_changes(self):
        before = self.enrollment.read_bytes()
        config, manager, original = installer.preflight(self.args)
        self.assertIs(config['panelbridge'], True)
        self.assertEqual(manager, 'lightdm.service')
        self.assertEqual(self.enrollment.read_bytes(), before)
        self.assertTrue(any(path == 'enrollment.json' for path, _ in self.opens))
        self.assertTrue(any(path == 'oled-integration.json' for path, _ in self.opens))
        self.assertTrue(all(not flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)
                            for _, flags in self.opens))

    def test_other_enrolled_account_is_rejected_before_staging(self):
        self.enrollment.write_text('{"api_version":1,"normal_uid":1001}')
        with self.assertRaisesRegex(ValueError, 'match.*enrolled desktop account'):
            installer.preflight(self.args)

    def test_missing_installation_reports_enrollment_missing(self):
        self.enrollment.unlink()
        with self.assertRaisesRegex(RuntimeError, 'PanelBridge enrollment.*missing'):
            installer.preflight(self.args)
        self.assertFalse(self.enrollment.exists())

    def test_cli_enable_requires_matching_enrollment_even_when_config_is_off(self):
        self.config.write_text('{"keys":true,"panelbridge":false}')
        self.args.panelbridge = True
        self.enrollment.write_text('{"api_version":1,"normal_uid":1001}')
        with self.assertRaisesRegex(ValueError, 'match.*enrolled desktop account'):
            installer.preflight(self.args)
        self.enrollment.write_text('{"api_version":1,"normal_uid":1000}')
        self.assertEqual(installer.preflight(self.args)[1], 'lightdm.service')
        self.capability.unlink()
        with self.assertRaisesRegex(RuntimeError, 'Update PanelBridge before enabling OLED integration'):
            installer.preflight(self.args)

    def test_invalid_device_integration_flag_is_not_coerced_into_enrollment(self):
        for raw in ('[]', '{"panelbridge":1}', '{"panelbridge":"true"}'):
            self.config.write_text(raw)
            with self.subTest(raw=raw), self.assertRaisesRegex(ValueError, 'panelbridge must be boolean'):
                installer.preflight(self.args)
        self.assertFalse(self.opens)

    def test_standalone_does_not_read_or_require_enrollment(self):
        self.enrollment.unlink()
        self.capability.unlink()
        for config in ('{"keys":true}', '{"keys":true,"panelbridge":false}'):
            self.config.write_text(config)
            self.assertEqual(installer.preflight(self.args)[1], 'lightdm.service')
            self.assertFalse(self.opens)

    def test_old_panelbridge_install_without_capability_requires_update(self):
        self.capability.unlink()
        with self.assertRaisesRegex(RuntimeError, 'Update PanelBridge before enabling OLED integration'):
            installer.preflight(self.args)
        self.assertFalse(self.capability.exists())

    def test_capability_requires_exact_supported_fields_and_types(self):
        valid = {'api_version': 1, 'startup_choice': 1, 'session_bus': 'org.panelbridge.Session1'}
        invalid = [None, [], {}, {**valid, 'extra': True}]
        for key in ('api_version', 'startup_choice'):
            invalid += [{**valid, key: value} for value in (True, 1.0, '1', 0, 2)]
        invalid += [{**valid, 'session_bus': 'org.other.Session1'},
                    {key: value for key, value in valid.items() if key != 'startup_choice'}]
        for receipt in invalid:
            self.capability.write_text(json.dumps(receipt))
            with self.subTest(receipt=receipt), self.assertRaisesRegex(RuntimeError, 'Update PanelBridge before enabling OLED integration'):
                installer.preflight(self.args)
        self.capability.write_text(json.dumps(valid))
        self.assertEqual(installer.preflight(self.args)[1], 'lightdm.service')

    def test_capability_malformed_or_oversized_requires_update(self):
        duplicate = '{"api_version":1,"startup_choice":0,"startup_choice":1,"session_bus":"org.panelbridge.Session1"}'
        for raw in ('not JSON', duplicate, self.capability.read_text() + ' ' * 65536):
            self.capability.write_text(raw)
            with self.assertRaisesRegex(RuntimeError, 'Update PanelBridge before enabling OLED integration'):
                installer.preflight(self.args)

    def test_capability_is_checked_through_the_same_root_trust_boundary(self):
        self.capability.chmod(0o666)
        with self.assertRaisesRegex(RuntimeError, 'Update PanelBridge before enabling OLED integration'):
            installer.preflight(self.args)
        self.capability.chmod(0o644)
        self.foreign_inode = self.capability.stat().st_ino
        with self.assertRaisesRegex(RuntimeError, 'Update PanelBridge before enabling OLED integration'):
            installer.preflight(self.args)

    def test_capability_symlink_is_not_a_valid_receipt(self):
        other = self.root / 'other-receipt.json'; other.write_bytes(self.capability.read_bytes())
        self.capability.unlink(); self.capability.symlink_to(other)
        with self.assertRaisesRegex(RuntimeError, 'Update PanelBridge before enabling OLED integration'):
            installer.preflight(self.args)

    def test_malformed_or_unsupported_enrollment_fails_closed(self):
        for raw in ('broken', '[]', '{}', '{"api_version":true,"normal_uid":1000}',
                    '{"api_version":2,"normal_uid":1000}', '{"api_version":1,"normal_uid":"1000"}',
                    '{"api_version":1,"normal_uid":true}', '{"api_version":1,"normal_uid":1001,"normal_uid":1000}',
                    '{"api_version":1,"normal_uid":1000}' + ' ' * 65536):
            self.enrollment.write_text(raw)
            with self.subTest(raw=raw[:80]), self.assertRaisesRegex(RuntimeError, 'PanelBridge enrollment.*invalid'):
                installer.preflight(self.args)

    def test_unsafe_file_owner_and_permissions_fail_closed(self):
        for mode, foreign in ((0o664, False), (0o644, True)):
            self.enrollment.chmod(mode)
            self.foreign_inode = self.enrollment.stat().st_ino if foreign else None
            with self.subTest(mode=mode, foreign=foreign), self.assertRaisesRegex(RuntimeError, 'PanelBridge enrollment.*unsafe'):
                installer.preflight(self.args)

    def test_unsafe_parent_owner_and_permissions_fail_closed(self):
        directory = self.enrollment.parent
        for mode, foreign in ((0o775, False), (0o755, True)):
            directory.chmod(mode)
            self.foreign_inode = directory.stat().st_ino if foreign else None
            with self.subTest(mode=mode, foreign=foreign), self.assertRaisesRegex(RuntimeError, 'PanelBridge enrollment.*unsafe'):
                installer.preflight(self.args)

    def test_enrollment_symlink_cannot_redirect_preflight(self):
        real = self.root / 'other.json'; real.write_bytes(self.enrollment.read_bytes())
        self.enrollment.unlink(); self.enrollment.symlink_to(real)
        with self.assertRaisesRegex(RuntimeError, 'PanelBridge enrollment.*unsafe'):
            installer.preflight(self.args)

    def test_parent_symlink_cannot_redirect_preflight(self):
        original = self.enrollment.parent
        moved = original.with_name('other'); original.rename(moved); original.symlink_to(moved)
        with self.assertRaisesRegex(RuntimeError, 'PanelBridge enrollment.*unsafe'):
            installer.preflight(self.args)

    def test_directory_and_hardlink_are_not_enrollment_files(self):
        self.enrollment.unlink(); self.enrollment.mkdir()
        with self.assertRaisesRegex(RuntimeError, 'PanelBridge enrollment.*unsafe'):
            installer.preflight(self.args)
        self.enrollment.rmdir(); self.enrollment.write_text('{"api_version":1,"normal_uid":1000}')
        os.link(self.enrollment, self.root / 'second-link')
        with self.assertRaisesRegex(RuntimeError, 'PanelBridge enrollment.*unsafe'):
            installer.preflight(self.args)


if __name__ == '__main__': unittest.main()

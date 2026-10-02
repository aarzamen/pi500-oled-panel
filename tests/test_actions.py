import importlib.machinery
import importlib.util
import json
import os
import subprocess
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


def helper_module():
    path = Path(__file__).resolve().parents[1] / 'system/oled-panel-action'
    loader = importlib.machinery.SourceFileLoader('action_helper', str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class HelperTests(unittest.TestCase):
    def setUp(self):
        self.helper = helper_module()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.runtime = self.root / 'run'
        self.runtime.mkdir()
        self.default = self.root / 'default'
        self.default.write_text('desktop\n')
        self.commands = []
        self.config = {'display_manager': 'lightdm.service'}

    def call(self, *args, runner=None):
        return self.helper.dispatch(list(args), self.config, self.runtime, self.default,
                                    runner or (lambda cmd: self.commands.append(cmd)))

    def test_only_exact_public_actions_are_allowed(self):
        for args in [(), ('reboot', 'now'), ('start-desktop', 'ssh.service'),
                     ('set-default', 'shell'), ('set-default', 'desktop', 'extra'),
                     ('/bin/sh',), ('selector-reset',), ('selector-finish',)]:
            with self.subTest(args=args), self.assertRaises(ValueError): self.call(*args)
        self.assertEqual(self.commands, [])

    def test_fixed_unit_and_marker_removed_before_start(self):
        (self.runtime / 'headless').write_text('headless')
        def run(cmd):
            self.assertFalse((self.runtime / 'headless').exists())
            self.commands.append(cmd)
        self.call('start-desktop', runner=run)
        self.assertEqual(self.commands, [['/usr/bin/systemctl', '--no-block', 'start', 'lightdm.service']])

    def test_all_effectful_commands_are_fixed(self):
        for action in ('stop-desktop', 'reboot', 'shutdown'): self.call(action)
        self.assertEqual(self.commands, [
            ['/usr/bin/systemctl', '--no-block', 'stop', 'lightdm.service'],
            ['/usr/bin/systemctl', '--no-block', 'reboot'],
            ['/usr/bin/systemctl', '--no-block', 'poweroff']])

    def test_invalid_manager_rejected(self):
        for name in ('--help', 'lightdm.service;reboot', '../../ssh.service', 'graphical.target'):
            self.config['display_manager'] = name
            with self.assertRaises(ValueError): self.call('start-desktop')
        self.assertFalse(self.commands)

    def test_saved_default_is_atomic_and_does_not_touch_boot_choice(self):
        (self.runtime / 'headless').write_text('current boot')
        old_inode = self.default.stat().st_ino
        self.call('set-default', 'headless')
        self.assertEqual(self.default.read_text(), 'headless\n')
        self.assertNotEqual(old_inode, self.default.stat().st_ino)
        self.assertEqual(self.default.stat().st_mode & 0o777, 0o644)
        self.assertEqual((self.runtime / 'headless').read_text(), 'current boot')
        self.assertFalse(self.commands)

    def test_runtime_symlink_cannot_redirect_root_cleanup(self):
        external = self.root / 'external'; external.mkdir()
        (external / 'headless').write_text('preserve')
        self.runtime.rmdir(); self.runtime.symlink_to(external)
        with self.assertRaises(OSError): self.call('start-desktop')
        self.assertTrue((external / 'headless').exists())
        self.assertFalse(self.commands)

    def test_cleanup_retains_success_and_removes_failure(self):
        for result in ('success', 'timeout', 'exit-code', 'signal', ''):
            (self.runtime / 'headless').write_text('headless')
            (self.runtime / 'choice.json').write_text('{}')
            self.helper.cleanup(self.runtime, result)
            self.assertEqual((self.runtime / 'headless').exists(), result == 'success')
            self.assertEqual((self.runtime / 'choice.json').exists(), result == 'success')

    def test_finish_quits_plymouth_only_for_headless(self):
        plymouth = self.root / 'plymouth'; plymouth.touch()
        self.helper.finish(self.runtime, plymouth=plymouth, runner=self.commands.append, running=lambda path: True)
        self.assertEqual(self.commands, [])
        (self.runtime / 'headless').write_text('headless')
        self.helper.finish(self.runtime, plymouth=plymouth, runner=self.commands.append, running=lambda path: True)
        self.assertEqual(self.commands, [[str(plymouth), 'quit']])
        self.assertTrue((self.runtime / 'headless').exists())

    def test_finish_without_plymouth_is_harmless(self):
        (self.runtime / 'headless').touch()
        self.helper.finish(self.runtime, plymouth=self.root / 'missing', runner=self.commands.append)
        self.assertEqual(self.commands, [])

    def test_finish_after_plymouth_already_exited_is_harmless(self):
        plymouth = self.root / 'plymouth'; plymouth.touch()
        (self.runtime / 'headless').touch()
        self.helper.finish(self.runtime, plymouth=plymouth, runner=self.commands.append,
                           running=lambda path: False)
        self.assertEqual(self.commands, [])
        self.assertTrue((self.runtime / 'headless').exists())

    def test_plymouth_probe_distinguishes_stopped_from_probe_error(self):
        for status, expected in ((0, True), (1, False), (2, None)):
            with self.subTest(status=status), patch.object(self.helper.subprocess, 'run') as run:
                run.return_value = subprocess.CompletedProcess([], status)
                if expected is None:
                    with self.assertRaises(RuntimeError):
                        self.helper.plymouth_running(Path('/usr/bin/plymouth'))
                else:
                    self.assertIs(self.helper.plymouth_running(Path('/usr/bin/plymouth')), expected)
                self.assertEqual(run.call_args.args[0], ['/usr/bin/plymouth', '--ping'])

    def test_quit_race_succeeds_only_if_plymouth_has_exited(self):
        plymouth = self.root / 'plymouth'; plymouth.touch()
        (self.runtime / 'headless').touch()
        def fail(command): raise subprocess.CalledProcessError(1, command)
        for still_running in (False, True):
            with self.subTest(still_running=still_running):
                probes = iter((True, still_running))
                if still_running:
                    with self.assertRaises(subprocess.CalledProcessError):
                        self.helper.finish(self.runtime, plymouth=plymouth, runner=fail,
                                           running=lambda path: next(probes))
                else:
                    self.helper.finish(self.runtime, plymouth=plymouth, runner=fail,
                                       running=lambda path: next(probes))

    def test_finish_failure_can_trigger_desktop_fallback(self):
        plymouth = self.root / 'plymouth'; plymouth.touch()
        (self.runtime / 'headless').touch()
        def fail(command): raise RuntimeError('plymouth quit failed')
        with self.assertRaises(RuntimeError):
            self.helper.finish(self.runtime, plymouth=plymouth, runner=fail, running=lambda path: True)
        self.helper.cleanup(self.runtime, 'exit-code')
        self.assertFalse((self.runtime / 'headless').exists())

    def test_root_config_rejects_symlinks_and_writable_permissions(self):
        target = self.root / 'config.json'; target.write_text('{}'); target.chmod(0o666)
        with self.assertRaises(PermissionError): self.helper.trusted_config(target)
        link = self.root / 'link'; link.symlink_to(target)
        with self.assertRaises((PermissionError, OSError)): self.helper.trusted_config(link)


if __name__ == '__main__': unittest.main()

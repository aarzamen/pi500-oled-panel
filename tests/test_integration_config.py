import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import mock_open, patch

from oled_panel.config import load_config
from oled_panel.runtime import read_boot_id, runtime_values


BOOT_ID = '11111111-1111-4111-8111-111111111111'


class IntegrationConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def load(self, supplied):
        path = self.root / 'device.json'
        path.write_text(json.dumps(supplied))
        return load_config(path)

    def test_standalone_default_remains_desktop_and_integration_off(self):
        config = load_config(None)
        self.assertEqual(config['boot_default'], 'Desktop')
        self.assertIs(config['panelbridge'], False)
        with self.assertRaises(ValueError):
            self.load({'boot_default': 'Wireless'})

    def test_only_literal_boolean_can_enable_integration(self):
        for value in (1, 0, 'true', None, [], {}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.load({'panelbridge': value})

    def test_integrated_saved_default_accepts_three_named_modes(self):
        for value in ('Wireless', 'Desktop', 'Headless'):
            with self.subTest(value=value):
                config = self.load({'panelbridge': True, 'boot_default': value})
                self.assertIs(config['panelbridge'], True)
                self.assertEqual(config['boot_default'], value)
        with self.assertRaises(ValueError):
            self.load({'panelbridge': True, 'boot_default': 'wireless'})

    def installed(self, enabled=True):
        etc, runtime = self.root / 'etc', self.root / 'run'
        etc.mkdir(); runtime.mkdir()
        (etc / 'actions.json').write_text(json.dumps({'display_manager': 'lightdm.service', 'panelbridge': enabled}))
        (etc / 'device.json').write_text(json.dumps({'panelbridge': enabled}))
        return etc, runtime

    def test_runtime_distinguishes_saved_choice_from_running_state(self):
        etc, runtime = self.installed()
        (etc / 'default').write_text('wireless\n')
        for mode, label in [('wireless', 'Wireless desktop'), ('desktop', 'Desktop only'), ('headless', 'Console only')]:
            (runtime / 'choice.json').write_text(json.dumps({'mode': mode, 'panelbridge': True, 'boot_id': BOOT_ID}))
            with patch('oled_panel.runtime.read_boot_id', return_value=BOOT_ID):
                values = runtime_values(etc, runtime)
            self.assertEqual(values['boot_default'], 'Wireless')
            self.assertEqual(values['one_time_mode'], label)
            self.assertNotIn('current_mode', values)

    def test_invalid_or_stale_integrated_choice_is_not_reported(self):
        etc, runtime = self.installed()
        (etc / 'default').write_text('desktop\n')
        for choice in ({'mode': 'wireless'},
                       {'mode': 'desktop', 'panelbridge': 1, 'boot_id': BOOT_ID},
                       {'mode': 'headless', 'panelbridge': True, 'boot_id': 'old'},
                       {'mode': 'invalid', 'panelbridge': True, 'boot_id': BOOT_ID}):
            (runtime / 'choice.json').write_text(json.dumps(choice))
            with patch('oled_panel.runtime.read_boot_id', return_value=BOOT_ID):
                values = runtime_values(etc, runtime)
            self.assertIsNone(values['one_time_mode'])

    def test_standalone_keeps_existing_runtime_labels_and_rejects_wireless(self):
        etc, runtime = self.installed(False)
        (etc / 'default').write_text('headless\n')
        (runtime / 'choice.json').write_text(json.dumps({'mode': 'desktop'}))
        self.assertEqual(runtime_values(etc, runtime), {
            'display_manager': 'lightdm.service', 'boot_default': 'Headless', 'one_time_mode': 'Desktop'})
        (etc / 'default').write_text('wireless\n')
        (runtime / 'choice.json').write_text(json.dumps({'mode': 'wireless'}))
        values = runtime_values(etc, runtime)
        self.assertIsNone(values['boot_default'])
        self.assertIsNone(values['one_time_mode'])

    def test_current_boot_id_is_bounded_and_requires_a_canonical_uuid(self):
        with patch.object(Path, 'open', mock_open(read_data=BOOT_ID + '\n')):
            self.assertEqual(read_boot_id(), BOOT_ID)
        for raw in ('', 'not-a-boot', BOOT_ID + ' trailing', BOOT_ID + ' ' * 50):
            with self.subTest(raw=raw), patch.object(Path, 'open', mock_open(read_data=raw)):
                with self.assertRaises(ValueError): read_boot_id()

    def test_missing_or_invalid_installed_enrollment_does_not_enable_wireless_labels(self):
        etc, runtime = self.installed()
        (etc / 'default').write_text('wireless\n')
        (runtime / 'choice.json').write_text(json.dumps({'mode': 'wireless', 'panelbridge': True, 'boot_id': BOOT_ID}))
        for raw in ('{}', '{"panelbridge":1}', '[]', 'broken'):
            (etc / 'device.json').write_text(raw)
            values = runtime_values(etc, runtime)
            self.assertIsNone(values['boot_default'])
            self.assertIsNone(values['one_time_mode'])
        (etc / 'device.json').unlink()
        self.assertIsNone(runtime_values(etc, runtime)['one_time_mode'])


if __name__ == '__main__': unittest.main()

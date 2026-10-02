import json
import subprocess
import unittest
from unittest.mock import Mock

from oled_panel.panelbridge import PanelBridgeClient


def reply(value):
    return subprocess.CompletedProcess([], 0, repr((json.dumps(value),)), '')


class PanelBridgeClientTests(unittest.TestCase):
    def test_status_uses_existing_local_user_bus_without_root(self):
        run = Mock(return_value=reply({'api_version': 1, 'status': 'streaming',
                                     'features': ['start', 'stop'],
                                     'profile': {'content_fps': 30}}))
        state = PanelBridgeClient(run, uid=1234).status()
        self.assertTrue(state['available'])
        self.assertEqual(state['actions'], ['monitor-start', 'monitor-stop'])
        self.assertEqual(run.call_args.args[0], [
            '/usr/bin/gdbus', 'call', '--address', 'unix:path=/run/user/1234/bus',
            '--dest', 'org.panelbridge.Session1', '--object-path', '/org/panelbridge/Session1',
            '--method', 'org.panelbridge.Session1.GetState'])
        self.assertEqual(run.call_args.kwargs['timeout'], 3)

    def test_disconnected_and_malformed_states_have_no_actions(self):
        bad = [reply({'api_version': True, 'status': 'streaming', 'features': []}),
               reply({'api_version': 1, 'status': 'surprise', 'features': []}),
               reply({'api_version': 1, 'status': [], 'features': []}),
               reply({'api_version': 1, 'status': 'streaming', 'features': 'start'}),
               subprocess.CompletedProcess([], 1, '', 'private error detail'),
               subprocess.CompletedProcess([], 0, 'not a response', ''),
               subprocess.CompletedProcess([], 0, 'x' * 131073, '')]
        for response in bad:
            with self.subTest(response=str(response)[:80]):
                value = PanelBridgeClient(Mock(return_value=response), uid=1234).status()
                self.assertEqual(value['state'], 'unavailable')
                self.assertEqual(value['actions'], [])
                self.assertNotIn('private', value['message'])
        for error in (FileNotFoundError(), subprocess.TimeoutExpired('gdbus', 3)):
            self.assertFalse(PanelBridgeClient(Mock(side_effect=error), uid=1234).status()['available'])

    def test_commands_are_fixed_and_rejections_remain_visible(self):
        run = Mock(return_value=reply({'api_version': 1, 'ok': True, 'result': {'accepted': True}}))
        client = PanelBridgeClient(run, uid=1234)
        client.command('monitor-start')
        self.assertEqual(run.call_args.args[0][-3:],
                         ['org.panelbridge.Session1.Command', 'start', '{}'])
        with self.assertRaises(ValueError):
            client.command('reboot; arbitrary command')
        self.assertEqual(run.call_count, 1)
        run.return_value = reply({'api_version': 1, 'ok': False, 'error': 'Unlock the desktop first'})
        with self.assertRaisesRegex(RuntimeError, 'Unlock'):
            client.command('monitor-start')

    def test_root_client_is_rejected(self):
        with self.assertRaises(ValueError):
            PanelBridgeClient(uid=0)

    def test_malformed_nested_values_do_not_become_visible_settings_or_trial(self):
        run = Mock(return_value=reply({'api_version': 1, 'status': 'streaming',
                                     'features': ['start'],
                                     'profile': {'source_width': True, 'content_fps': ['bad']},
                                     'trial': {'kind': 'profile', 'seconds_remaining': float('nan')}}))
        state = PanelBridgeClient(run, uid=1234).status()
        self.assertEqual(state['profile'], {})
        self.assertIsNone(state['trial'])
        self.assertEqual(state['actions'], ['monitor-start'])

    def test_command_requires_current_protocol_and_positive_acknowledgment(self):
        for payload in ({'ok': True, 'result': {'accepted': True}},
                        {'api_version': True, 'ok': True, 'result': {'accepted': True}},
                        {'api_version': 1, 'ok': True, 'result': {'accepted': False}},
                        {'api_version': 1, 'ok': True, 'result': None}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                PanelBridgeClient(Mock(return_value=reply(payload)), uid=1234).command('monitor-start')

    def test_full_profile_is_preserved_for_trial_revalidation(self):
        profile = {'source_width': 1280, 'source_height': 720, 'content_fps': 30,
                   'wire_width': 1280, 'wire_height': 720, 'wire_fps': 30,
                   'bitrate_kbps': 4096, 'scale': 2, 'rotation': 0}
        client = PanelBridgeClient(Mock(return_value=reply({
            'api_version': 1, 'status': 'streaming', 'features': [], 'profile': profile})), uid=1234)
        self.assertEqual(client.status()['profile'], profile)


if __name__ == '__main__':
    unittest.main()

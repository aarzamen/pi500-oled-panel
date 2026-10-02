"""Synthetic OLED interaction tests; no GPIO, bus or controller calls."""
import time
import unittest

from oled_panel import ui


def status(state='stopped', *, actions=None, trial=None, available=True):
    return {'available': available, 'state': state, 'message': 'Synthetic controller message',
            'profile': {'source_width': 1280, 'source_height': 720, 'content_fps': 15,
                        'wire_width': 1280, 'wire_height': 720, 'wire_fps': 30},
            'receiver': {'name': 'Example monitor'}, 'trial': trial,
            'actions': ['monitor-start', 'monitor-stop', 'monitor-keep', 'monitor-revert']
            if actions is None else actions}


def sample(controller=None, age=0):
    return {'sampled_at': time.time(), 'addresses': ['192.0.2.20'],
            'panelbridge': controller if controller is not None else status(),
            'panelbridge_sampled_at': time.time() - age}


def press(state, key, now=1):
    state, action = ui.update_ui(state, {'type': 'key_down', 'key': key}, now)
    ui.update_ui(state, {'type': 'key_up', 'key': key}, now + .01)
    return action


def integrated(controller=None, age=0):
    state = ui.initial_state(panelbridge=True, boot_default='Desktop')
    ui.update_ui(state, {'type': 'snapshot', 'snapshot': sample(controller, age)}, 0)
    return state


class MonitorUiTests(unittest.TestCase):
    def test_optional_home_first_navigation_preserves_all_seven_existing_pages(self):
        state = integrated()
        self.assertEqual(ui.page_names(state), ('Monitor', 'Home', 'Network', 'Compute', 'Thermal', 'Power', 'Storage', 'Workload'))
        press(state, 'up')
        self.assertEqual(state.page, 7)
        press(state, 'down')
        self.assertEqual(state.page, 0)
        standalone = ui.initial_state()
        press(standalone, 'up')
        self.assertEqual(standalone.page, 6)
        self.assertEqual(len(ui.menu_items(standalone)), 5)

    def test_monitor_home_shows_controller_state_source_rate_and_actual_lan_address(self):
        state = integrated(status('streaming'))
        lines = ' '.join(ui._lines(state, state.snapshot))
        for value in ('Streaming', '1280x720', '15 fps', '192.0.2.20'):
            self.assertIn(value, lines)
        image = ui.render_ui(state, state.snapshot)
        self.assertEqual((image.mode, image.size), ('1', (128, 64)))
        self.assertTrue(image.getbbox())

    def test_monitor_submenu_uses_capabilities_and_current_state(self):
        cases = [('stopped', None, ['monitor-start']),
                 ('connecting', None, ['monitor-stop']),
                 ('streaming', None, ['monitor-stop']),
                 ('error', None, ['monitor-start', 'monitor-stop', 'monitor-revert']),
                 ('connecting', {'kind': 'profile', 'seconds_remaining': 0}, ['monitor-stop', 'monitor-revert']),
                 ('streaming', {'kind': 'profile', 'seconds_remaining': 9}, ['monitor-stop', 'monitor-keep', 'monitor-revert']),
                 ('streaming', {'kind': 'profile', 'seconds_remaining': 0}, ['monitor-stop', 'monitor-revert'])]
        for current, trial, expected in cases:
            with self.subTest(state=current, trial=trial):
                self.assertEqual([action for _, action in ui.monitor_actions(status(current, trial=trial))], expected)
        self.assertEqual(ui.monitor_actions(status('error', actions=[])), [])
        self.assertEqual(ui.monitor_actions(status(available=False)), [])

    def test_stale_or_missing_controller_never_exposes_cached_actions(self):
        for controller, age in ((status('streaming'), 4), ({}, 0), (status(available=False), 0)):
            state = integrated(controller, age)
            press(state, 'back')
            press(state, 'select')
            self.assertEqual(state.view, 'monitor-menu')
            self.assertEqual(ui.monitor_menu_items(state), [('Details', 'monitor-details')])
            self.assertIn('Unavailable', ' '.join(ui._lines(ui.initial_state(panelbridge=True), {})))

    def test_trial_expiration_while_menu_open_prevents_keep(self):
        state = integrated(status('streaming', trial={'kind': 'profile', 'seconds_remaining': 4}))
        press(state, 'back'); press(state, 'select'); press(state, 'down')
        self.assertEqual(ui.monitor_menu_items(state)[state.monitor_index][1], 'monitor-keep')
        ui.update_ui(state, {'type': 'snapshot', 'snapshot': sample(status('streaming'))}, 2)
        self.assertIsNone(press(state, 'select', 3))
        self.assertEqual(state.view, 'detail')

    def test_expired_keep_row_cannot_turn_into_revert_under_the_same_finger(self):
        state = integrated(status('streaming', trial={'kind': 'profile', 'seconds_remaining': 4}))
        press(state, 'back'); press(state, 'select'); press(state, 'down')
        ui.update_ui(state, {'type': 'snapshot', 'snapshot': sample(status('streaming', trial={
            'kind': 'profile', 'seconds_remaining': 0}))}, 2)
        self.assertIsNone(press(state, 'select', 3))

    def test_remaining_trial_time_accounts_for_status_age(self):
        state = integrated(status('streaming', trial={'kind': 'profile', 'seconds_remaining': 1}), age=2)
        self.assertNotIn('monitor-keep', [action for _, action in ui.monitor_menu_items(state)])

    def test_error_offers_reconnect_and_restore_using_fixed_commands(self):
        state = integrated(status('error'))
        press(state, 'back'); press(state, 'select')
        self.assertEqual(ui.monitor_menu_items(state)[0], ('Reconnect', 'monitor-start'))
        self.assertIn(('Restore last good', 'monitor-revert'), ui.monitor_menu_items(state))
        self.assertEqual(press(state, 'select'), 'monitor-start')

    def test_selected_last_main_menu_item_remains_visible(self):
        state = integrated()
        press(state, 'back'); press(state, 'up')
        lines = ui._lines(state, state.snapshot)
        self.assertLessEqual(len(lines), 5)
        self.assertIn('>Boot Default', lines)
        press(state, 'select')
        self.assertEqual(state.view, 'default')

    def test_three_saved_defaults_map_to_fixed_actions_without_changing_saved_value(self):
        for index, expected in enumerate(('wireless', 'desktop', 'headless')):
            state = integrated()
            state.view = 'default'; state.default_index = index
            press(state, 'select')
            ui.update_ui(state, {'type': 'key_down', 'key': 'select'}, 2)
            _, action = ui.update_ui(state, {'type': 'tick'}, 4)
            self.assertEqual(action, 'set-default ' + expected)
            self.assertEqual(state.boot_default, 'Desktop')

    def test_long_controller_message_and_receiver_have_reachable_details(self):
        controller = status('error')
        controller['message'] = 'Try the normal desktop. ' * 14 + 'END MARKER'
        state = integrated(controller)
        press(state, 'select')
        contents = ''.join(''.join(lines) for _, lines in ui.detail_pages(state, state.snapshot))
        self.assertIn(controller['message'], contents)
        self.assertIn('Example monitor', contents)
        self.assertIn('192.0.2.20', contents)

    def test_integrated_wake_gesture_cannot_start_monitor(self):
        state = integrated()
        state.view = 'monitor-menu'
        ui.update_ui(state, {'type': 'tick'}, 60)
        self.assertIsNone(press(state, 'select', 61))
        self.assertEqual(state.view, 'monitor-menu')
        self.assertEqual(press(state, 'select', 62), 'monitor-start')

    def test_integrated_shutdown_still_requires_release_and_fresh_hold(self):
        state = integrated()
        press(state, 'back')
        for _ in range(4): press(state, 'down')
        ui.update_ui(state, {'type': 'key_down', 'key': 'select'}, 1)
        _, action = ui.update_ui(state, {'type': 'tick'}, 5)
        self.assertIsNone(action)
        ui.update_ui(state, {'type': 'key_up', 'key': 'select'}, 5.1)
        ui.update_ui(state, {'type': 'key_down', 'key': 'select'}, 6)
        _, action = ui.update_ui(state, {'type': 'tick'}, 8)
        self.assertEqual(action, 'shutdown')

    def test_busy_monitor_disables_duplicate_commands(self):
        state = integrated()
        state.monitor_pending = True
        state.view = 'monitor-menu'
        self.assertIsNone(press(state, 'select'))


if __name__ == '__main__':
    unittest.main()

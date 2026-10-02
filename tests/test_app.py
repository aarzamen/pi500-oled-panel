import json
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from oled_panel.app import KeyEdges, main, run_foreground
from oled_panel.config import load_config


class ConfigTests(unittest.TestCase):
    def test_rejects_invalid_button_configuration(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.json"
            path.write_text(json.dumps({"pins": [17, 17, 22, 23]}))
            with self.assertRaisesRegex(ValueError, "pins"):
                load_config(path)

    def test_rejects_unbounded_or_unlabeled_sources(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.json"
            for bad in ({"workload": {"type": "endpoint", "url": "file:///etc/passwd"}},
                        {"power": {"path": "/tmp/value", "scale": 1}}):
                path.write_text(json.dumps(bad))
                with self.subTest(bad=bad), self.assertRaises(ValueError):
                    load_config(path)


class AppTests(unittest.TestCase):
    def test_keys_held_at_start_do_not_emit_press(self):
        edges = KeyEdges({"select"})
        self.assertEqual(edges.events({"select"}), [])
        self.assertEqual(edges.events(set()), [{"type": "key_up", "key": "select"}])
        self.assertEqual(edges.events({"select"}), [{"type": "key_down", "key": "select"}])

    def test_snapshot_and_preview_need_no_hardware(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            with patch("oled_panel.app.PanelHardware", side_effect=AssertionError("hardware touched")):
                self.assertEqual(main(["--preview-dir", str(path), "--dry-run-actions"]), 0)
                self.assertEqual(len(list(path.glob("*.png"))), 7)
                self.assertEqual(main(["--snapshot", "--dry-run-actions"]), 0)

    def test_real_actions_are_rejected(self):
        with self.assertRaises(SystemExit):
            main(["--foreground", "--seconds", "0.1"])

    def test_foreground_logs_action_without_executing_it(self):
        class FakePanel:
            def __init__(self):
                self.calls = 0
                self.closed = False
            def read_keys(self):
                self.calls += 1
                sequence = [set(), {"back"}, set(), {"down"}, set(),
                            {"down"}, set(), {"select"}, set()]
                return sequence[self.calls - 1] if self.calls <= len(sequence) else {"select"}
            def show(self, image):
                pass
            def close(self):
                self.closed = True
        panel = FakePanel()
        class NoThread:
            def __init__(self, *args, **kwargs):
                pass
            def start(self):
                pass
        clock = iter(index / 10 for index in range(200))
        output = io.StringIO()
        with patch("oled_panel.app.Thread", NoThread), \
             patch("oled_panel.app.time.monotonic", side_effect=lambda: next(clock)), \
             patch("oled_panel.app.time.sleep", return_value=None), \
             contextlib.redirect_stdout(output):
            run_foreground(panel, load_config(None), seconds=6)
        self.assertTrue(panel.closed)
        self.assertEqual(output.getvalue().count("DRY RUN action: reboot"), 1)


if __name__ == "__main__":
    unittest.main()


class InstalledAppTests(unittest.TestCase):
    def test_action_failure_stays_visible_until_dismissed(self):
        from oled_panel.app import perform_action
        from oled_panel.ui import initial_state, update_ui, _lines
        state = initial_state()
        def denied(action): raise RuntimeError('sudo denied')
        perform_action(state, 'start-desktop', denied)
        state, _ = update_ui(state, {'type': 'snapshot', 'snapshot': {}}, 1)
        self.assertEqual(state.view, 'action-error')
        self.assertIn('sudo denied', ' '.join(_lines(state, {})))
        state, action = update_ui(state, {'type': 'key_down', 'key': 'back'}, 2)
        self.assertEqual(state.view, 'page')
        self.assertIsNone(action)

    def test_dispatch_uses_exact_sudo_helper_and_rejects_unknown_action(self):
        from oled_panel.app import dispatch_action
        import subprocess
        with patch('oled_panel.app.subprocess.run') as run:
            run.return_value = subprocess.CompletedProcess([], 0, '', '')
            dispatch_action('set-default headless')
            self.assertEqual(run.call_args.args[0], ['/usr/bin/sudo', '-n', '/usr/local/libexec/oled-panel-action', 'set-default', 'headless'])
            with self.assertRaises(ValueError): dispatch_action('reboot now')
            self.assertEqual(run.call_count, 1)

    def test_runtime_values_override_static_config_without_effectful_actions(self):
        from oled_panel.runtime import runtime_values
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); etc = root / 'etc'; runtime = root / 'run'
            etc.mkdir(); runtime.mkdir()
            (etc / 'actions.json').write_text(json.dumps({'display_manager': 'lightdm.service'}))
            (etc / 'default').write_text('headless\n')
            (runtime / 'choice.json').write_text(json.dumps({'mode': 'desktop'}))
            values = runtime_values(etc, runtime)
            self.assertEqual(values, {'display_manager': 'lightdm.service', 'boot_default': 'Headless', 'one_time_mode': 'Desktop'})
            (etc / 'default').write_text('broken')
            (runtime / 'choice.json').write_text('broken')
            values = runtime_values(etc, runtime)
            self.assertIsNone(values['boot_default'])
            self.assertIsNone(values['one_time_mode'])

    def test_daemon_sigterm_closes_panel_and_restores_signal_handler(self):
        import signal
        class Panel:
            closed = False
            frames = 0
            def read_keys(self): return set()
            def show(self, frame):
                self.frames += 1
                signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
            def close(self): self.closed = True
        panel = Panel()
        old = signal.getsignal(signal.SIGTERM)
        class NoThread:
            def __init__(self, **kwargs): pass
            def start(self): pass
        with patch('oled_panel.app.PanelHardware', return_value=panel), patch('oled_panel.app.Thread', NoThread):
            self.assertEqual(main(['--daemon', '--dry-run-actions']), 0)
        self.assertTrue(panel.closed)
        self.assertEqual(panel.frames, 1)
        self.assertIs(signal.getsignal(signal.SIGTERM), old)

    def test_foreground_action_failure_keeps_rendering_and_closes(self):
        from oled_panel.ui import initial_state, _lines
        panel = type('Panel', (), {'read_keys': lambda self: set(),
                                  'close': lambda self: setattr(self, 'closed', True),
                                  'show': lambda self, image: None})()
        class NoThread:
            def __init__(self, **kwargs): pass
            def start(self): pass
        state = initial_state()
        pending = ['reboot']
        rendered = []
        def update(current, event, now): return current, pending.pop() if pending else None
        def render(current, snapshot):
            rendered.append(current.view)
            from PIL import Image
            return Image.new('1', (128,64))
        clock = iter(i / 10 for i in range(200))
        def denied(action): raise RuntimeError('denied')
        with patch('oled_panel.app.Thread', NoThread), patch('oled_panel.app.initial_state', return_value=state), \
             patch('oled_panel.app.update_ui', side_effect=update), patch('oled_panel.app.render_ui', side_effect=render), \
             patch('oled_panel.app.time.monotonic', side_effect=lambda: next(clock)), patch('oled_panel.app.time.sleep'):
            run_foreground(panel, load_config(None), seconds=2, dispatch=denied)
        self.assertGreater(len(rendered), 1)
        self.assertTrue(all(view == 'action-error' for view in rendered))
        self.assertTrue(panel.closed)

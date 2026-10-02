import json
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from oled_panel import boot


class Clock:
    def __init__(self): self.now = 0.0
    def monotonic(self): return self.now
    def sleep(self, delay): self.now += delay


class Panel:
    def __init__(self, clock, keys=lambda t: set(), fail=None):
        self.clock, self.keys, self.fail = clock, keys, fail
        self.closed = False
        self.frames = []
    def read_keys(self):
        if self.fail == 'keys': raise OSError('key failure')
        return self.keys(self.clock.now)
    def show(self, frame):
        if self.fail == 'render': raise OSError('render failure')
        if len(self.frames) < 2:
            self.frames.append((self.clock.now, frame.copy()))
    def close(self):
        self.closed = True
        if self.fail == 'close': raise OSError('cleanup failure')


class BootTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = {'boot_default': 'Desktop', 'runtime_dir': str(self.root)}
        self.clock = Clock()

    def choose(self, keys=lambda t: set(), fail=None):
        self.panel = Panel(self.clock, keys, fail)
        return boot.choose_boot_mode(self.config, lambda: self.panel, self.clock)

    def test_original_george_splash_then_full_eight_second_chooser(self):
        self.assertEqual(self.choose(), 'desktop')
        self.assertGreaterEqual(self.clock.now, 10)
        self.assertLess(self.clock.now, 10.1)
        splash_time, splash = self.panel.frames[0]
        chooser_time, chooser = self.panel.frames[1]
        self.assertEqual(splash_time, 0)
        self.assertEqual((splash.size, splash.mode), ((128, 64), '1'))
        self.assertEqual(hashlib.sha256(splash.tobytes()).hexdigest(),
                         '52fabb6b40d1e525336e2876e7b4c3fff27f55711e39a0012771ba627a8e347d')
        self.assertEqual(chooser_time, 2)
        self.assertNotEqual(splash.tobytes(), chooser.tobytes())
        self.assertTrue(self.panel.closed)
        self.assertFalse((self.root / 'headless').exists())

    def test_navigation_pauses_idle_but_caps_at_thirty_seconds(self):
        self.assertEqual(self.choose(lambda t: {'down'} if int(t * 4) % 2 else set()), 'desktop')
        self.assertGreaterEqual(self.clock.now, 30)
        self.assertLess(self.clock.now, 30.1)

    def test_confirmed_headless_does_not_change_saved_default(self):
        keys = lambda t: {'down'} if 3 <= t < 4 else ({'select'} if 5 <= t else set())
        self.assertEqual(self.choose(keys), 'headless')
        self.assertEqual(self.config['boot_default'], 'Desktop')
        self.assertEqual(json.loads((self.root / 'choice.json').read_text())['mode'], 'headless')
        self.assertTrue((self.root / 'headless').exists())

    def test_cancel_uses_saved_default(self):
        self.config['boot_default'] = 'Headless'
        self.assertEqual(self.choose(lambda t: {'back'} if t >= 3 else set()), 'headless')
        self.assertLess(self.clock.now, 3.1)

    def test_key_held_across_splash_does_not_confirm(self):
        self.assertEqual(self.choose(lambda t: {'select'} if t >= 1 else set()), 'desktop')
        self.assertGreaterEqual(self.clock.now, 10)

    def test_missing_artwork_still_offers_the_chooser(self):
        with patch('oled_panel.boot.load_splash', side_effect=OSError('missing art')):
            self.assertEqual(self.choose(), 'desktop')
        self.assertGreaterEqual(self.clock.now, 8)
        self.assertLess(self.clock.now, 8.1)
        self.assertTrue(self.panel.closed)

    def test_held_select_at_start_never_confirms(self):
        self.assertEqual(self.choose(lambda t: {'select'}), 'desktop')
        self.assertGreaterEqual(self.clock.now, 8)

    def test_stale_headless_is_removed_before_hardware_init(self):
        (self.root / 'headless').write_text('old')
        (self.root / 'choice.json').write_text('old')
        def hardware():
            self.assertFalse((self.root / 'headless').exists())
            self.assertFalse((self.root / 'choice.json').exists())
            raise OSError('missing OLED')
        self.assertEqual(boot.choose_boot_mode(self.config, hardware, self.clock), 'desktop')

    def test_failures_never_leave_a_skip_marker(self):
        keys = lambda t: {'down'} if 3 <= t < 4 else ({'select'} if t >= 5 else set())
        for failure in ('keys', 'render', 'close'):
            with self.subTest(failure=failure):
                self.clock.now = 0
                self.assertEqual(self.choose(keys, failure), 'desktop')
                self.assertTrue(self.panel.closed)
                self.assertFalse((self.root / 'headless').exists())

    def test_invalid_config_never_opens_hardware(self):
        self.config['boot_default'] = 'invalid'
        self.assertEqual(boot.choose_boot_mode(self.config, lambda: self.fail('opened'), self.clock), 'desktop')

    def test_atomic_failure_leaves_no_headless_marker(self):
        keys = lambda t: {'down'} if 3 <= t < 4 else ({'select'} if t >= 5 else set())
        with patch('oled_panel.boot.os.replace', side_effect=OSError('full')):
            self.assertEqual(self.choose(keys), 'desktop')
        self.assertFalse((self.root / 'headless').exists())
        self.assertEqual(list(self.root.glob('.*.tmp')), [])

    def test_commit_happens_only_after_close(self):
        panel = Panel(self.clock)
        def close(): self.assertFalse((self.root / 'choice.json').exists())
        panel.close = close
        self.assertEqual(boot.choose_boot_mode(self.config, lambda: panel, self.clock), 'desktop')


if __name__ == '__main__': unittest.main()

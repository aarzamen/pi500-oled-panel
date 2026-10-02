"""Mac tests for the diagnostic's validation, frames, and resource cleanup."""
import contextlib
import io
import unittest
from unittest.mock import patch

import hardware_check as check


class DiagnosticTests(unittest.TestCase):
    def parse(self, *args):
        with contextlib.redirect_stderr(io.StringIO()):
            return check.parse_args(list(args))

    def test_hardware_requires_explicit_bus_and_address(self):
        for args in [[], ["--bus", "1"], ["--address", "0x3c"]]:
            with self.subTest(args=args), self.assertRaises(SystemExit):
                self.parse(*args)

    def test_buttons_require_polarity_chip_and_conflict_check(self):
        base = ["--bus", "1", "--address", "0x3c", "--keys"]
        for more in [[], ["--polarity", "low"],
                     ["--polarity", "low", "--gpiochip", "0"]]:
            with self.subTest(more=more), self.assertRaises(SystemExit):
                self.parse(*(base + more))
        args = self.parse(*(base + ["--polarity", "low", "--gpiochip", "0",
                                   "--pins-checked"]))
        self.assertEqual(args.address, 60)

    def test_invalid_hardware_values_rejected(self):
        for more in [["--seconds", "0"], ["--seconds", "nan"],
                     ["--seconds", "inf"], ["--bus", "-1"],
                     ["--address", "0x40"], ["--rotate", "1"]]:
            with self.subTest(more=more), self.assertRaises(SystemExit):
                self.parse("--bus", "1", "--address", "0x3c", *more)

    def test_preview_needs_no_hardware_config(self):
        self.assertEqual(str(self.parse("--preview", "preview.png").preview),
                         "preview.png")

    def test_frame_has_physical_boundary_and_edges(self):
        frame = check.render_check(set(), keys_enabled=False)
        self.assertEqual((frame.mode, frame.size), ("1", (128, 64)))
        for point in [(0, 0), (127, 0), (0, 63), (127, 63), (60, 15)]:
            self.assertNotEqual(frame.getpixel(point), 0)
        self.assertEqual(frame.getpixel((60, 16)), 0)

    def test_each_pressed_key_changes_its_own_row(self):
        off = check.render_check(set(), keys_enabled=True)
        for index, name in enumerate(["up", "down", "select", "back"]):
            on = check.render_check({name}, keys_enabled=True)
            for row in range(4):
                box = (2, 18 + 11 * row, 126, 29 + 11 * row)
                if row == index:
                    self.assertNotEqual(on.crop(box).tobytes(), off.crop(box).tobytes())
                else:
                    self.assertEqual(on.crop(box).tobytes(), off.crop(box).tobytes())

    def test_display_failure_still_closes_hardware(self):
        class FailedPanel:
            closed = False
            def read_keys(self):
                return set()
            def show(self, frame):
                raise OSError("display disconnected")
            def close(self):
                self.closed = True
        panel = FailedPanel()
        with self.assertRaises(OSError):
            check.run_check(panel, seconds=1, keys_enabled=False)
        self.assertTrue(panel.closed)

    def test_non_pi_refused_before_hardware_import(self):
        args = self.parse("--bus", "1", "--address", "0x3c")
        with patch.object(check, "read_model", return_value="MacBook Pro"):
            with self.assertRaisesRegex(RuntimeError, "Pi 500"):
                check.PanelHardware(args)


if __name__ == "__main__":
    unittest.main()

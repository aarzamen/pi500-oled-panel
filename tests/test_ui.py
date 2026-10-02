import unittest

from oled_panel.ui import initial_state, update_ui, render_ui, detail_pages


def step(state, kind, now, key=None):
    event = {"type": kind}
    if key:
        event["key"] = key
    return update_ui(state, event, now)


class UiTests(unittest.TestCase):
    def test_navigation_wraps_seven_pages(self):
        state = initial_state(now=0)
        state, _ = step(state, "key_down", 1, "up")
        self.assertEqual(state.page, 6)
        state, _ = step(state, "key_down", 2, "down")
        self.assertEqual(state.page, 0)

    def test_first_press_after_blank_only_wakes_entire_gesture(self):
        state = initial_state(now=0)
        state, _ = step(state, "tick", 60)
        self.assertTrue(state.blank)
        state, action = step(state, "key_down", 61, "down")
        self.assertFalse(state.blank)
        self.assertEqual(state.page, 0)
        self.assertIsNone(action)
        state, _ = step(state, "key_up", 62, "down")
        self.assertEqual(state.page, 0)
        state, _ = step(state, "key_down", 63, "down")
        self.assertEqual(state.page, 1)

    def test_chord_added_during_wake_does_not_navigate(self):
        state = initial_state(now=0)
        state, _ = step(state, "tick", 60)
        state, _ = step(state, "key_down", 61, "up")
        state, _ = step(state, "key_down", 61.1, "down")
        state, _ = step(state, "key_up", 61.2, "up")
        state, _ = step(state, "key_down", 61.3, "back")
        self.assertEqual((state.page, state.view), (0, "page"))
        state, _ = step(state, "key_up", 61.4, "down")
        state, _ = step(state, "key_up", 61.5, "back")
        state, _ = step(state, "key_down", 62, "back")
        self.assertEqual(state.view, "menu")

    def enter_reboot_confirmation(self):
        state = initial_state(now=0)
        state, _ = step(state, "key_down", 0.1, "back")
        for index in range(2):
            state, _ = step(state, "key_down", index + 1, "down")
        state, _ = step(state, "key_down", 3, "select")
        self.assertEqual(state.view, "confirm")
        return state

    def test_confirmation_requires_fresh_two_second_hold_once(self):
        state = self.enter_reboot_confirmation()
        state, action = step(state, "tick", 8)
        self.assertIsNone(action)
        state, _ = step(state, "key_up", 8.1, "select")
        state, _ = step(state, "key_down", 9, "select")
        state, action = step(state, "tick", 10.9)
        self.assertIsNone(action)
        state, action = step(state, "tick", 11)
        self.assertEqual(action, "reboot")
        state, action = step(state, "tick", 12)
        self.assertIsNone(action)
        state, action = step(state, "key_up", 12.1, "select")
        self.assertIsNone(action)

    def test_cancel_emits_no_action(self):
        state = self.enter_reboot_confirmation()
        state, action = step(state, "key_down", 4, "back")
        self.assertIsNone(action)
        self.assertEqual(state.view, "menu")

    def test_boot_default_selection_only_emits_dry_run_action(self):
        state = initial_state(now=0, boot_default="Desktop")
        state, _ = step(state, "key_down", 1, "back")
        for index in range(4):
            state, _ = step(state, "key_down", 2 + index, "down")
        state, action = step(state, "key_down", 6, "select")
        self.assertEqual((state.view, action), ("default", None))
        state, _ = step(state, "key_up", 6.1, "select")
        state, _ = step(state, "key_down", 7, "down")
        state, _ = step(state, "key_down", 8, "select")
        self.assertEqual(state.view, "confirm")
        state, _ = step(state, "key_up", 8.1, "select")
        state, _ = step(state, "key_down", 9, "select")
        state, action = step(state, "tick", 11)
        self.assertEqual(action, "set-default headless")
        self.assertEqual(state.boot_default, "Desktop")

    def test_frames_are_bounded_one_bit_on_every_page(self):
        snapshot = {"sampled_at": 1, "addresses": ["192.0.2.97", "2001:db8:" + "a" * 80],
                    "hostname": "pi500", "cpu_percent": 12, "ram_available_bytes": 2**30,
                    "ram_total_bytes": 8 * 2**30, "temperature_c": 44,
                    "root_free_bytes": 9 * 2**30, "uptime_s": 90,
                    "power_watts": None, "power_scope": None,
                    "workload_state": "Not configured", "current_mode": "Desktop",
                    "boot_default": "Desktop"}
        for page in range(7):
            with self.subTest(page=page):
                state = initial_state(now=1)
                state.page = page
                image = render_ui(state, snapshot)
                self.assertEqual((image.mode, image.size), ("1", (128, 64)))
                self.assertNotEqual(image.getbbox(), None)

    def test_stale_snapshot_renders_unavailable(self):
        state = initial_state(now=0)
        old = render_ui(state, {"sampled_at": 1, "addresses": ["192.0.2.97"]})
        fresh = render_ui(state, {"sampled_at": __import__("time").time(),
                                  "addresses": ["192.0.2.97"]})
        self.assertNotEqual(old.tobytes(), fresh.tobytes())

    def test_one_time_mode_is_distinct_from_saved_default(self):
        state = initial_state(now=0, current_mode="Headless", boot_default="Desktop")
        state, _ = update_ui(state, {"type": "snapshot", "snapshot": {"one_time_mode": "Headless"}}, 1)
        self.assertEqual(state.one_time_mode, "Headless")
        self.assertEqual(state.boot_default, "Desktop")
        sample = {"sampled_at": __import__("time").time(), "addresses": ["192.0.2.97"]}
        state.view = "detail"
        state.detail_index = 3
        headless = render_ui(state, sample)
        state.one_time_mode = "Desktop"
        desktop = render_ui(state, sample)
        self.assertNotEqual(headless.tobytes(), desktop.tobytes())

    def test_select_cycles_complete_detail_values(self):
        sample = {"sampled_at": __import__("time").time(),
                  "hostname": "pi-very-long-hostname", "addresses": ["2001:db8:1234:5678:9abc:def0:1234:5678"],
                  "interfaces": [{"name": "wlan0", "link_state": "up",
                                  "addresses": ["2001:db8:1234:5678:9abc:def0:1234:5678"]}],
                  "current_mode": "Headless", "one_time_mode": "Headless",
                  "boot_default": "Desktop"}
        state = initial_state(now=0)
        state.page = 1
        pages = detail_pages(state, sample)
        self.assertIn("2001:db8:1234:5678:9abc:def0:1234:5678",
                      "".join("".join(lines) for _, lines in pages))
        state, _ = update_ui(state, {"type": "snapshot", "snapshot": sample}, 0)
        state, _ = step(state, "key_down", 1, "select")
        self.assertEqual(state.view, "detail")
        first = render_ui(state, sample).tobytes()
        state, _ = step(state, "key_down", 2, "select")
        self.assertNotEqual(first, render_ui(state, sample).tobytes())
        state, _ = step(state, "key_down", 3, "down")
        self.assertEqual((state.page, state.view), (2, "page"))

    def test_each_required_page_has_reachable_readings(self):
        sample = {"sampled_at": __import__("time").time(), "hostname": "raspberrypi",
                  "addresses": ["192.0.2.97"], "current_mode": "Desktop",
                  "interfaces": [{"name": "wlan0", "link_state": "up", "addresses": ["192.0.2.97"]}],
                  "cpu_percent": 17, "load_average": [1.1, 0.9, 0.8],
                  "ram_used_bytes": 2**30, "ram_available_bytes": 7 * 2**30,
                  "ram_total_bytes": 8 * 2**30, "temperature_c": 43,
                  "throttle_flags": {"current": {"under_voltage": False, "throttled": False},
                                     "history": {"under_voltage": True, "throttled": False}},
                  "supply_warning": "Past undervoltage", "power_watts": None,
                  "power_scope": None, "root_used_bytes": 16 * 2**30,
                  "root_free_bytes": 13 * 2**30, "uptime_s": 7200,
                  "workload_state": "Not configured"}
        expected = ["raspberrypi", "192.0.2.97", "wlan0", "up", "1.1", "7.0", "43",
                    "Past undervoltage", "16.0", "13.0", "2h", "Not configured"]
        content = []
        for page in range(7):
            state = initial_state(now=0)
            state.page = page
            content.extend(label + "".join(lines) for label, lines in detail_pages(state, sample))
        joined = " ".join(content)
        for value in expected:
            with self.subTest(value=value):
                self.assertIn(value, joined)


if __name__ == "__main__":
    unittest.main()

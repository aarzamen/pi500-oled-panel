import unittest
from unittest.mock import patch

from oled_panel.metrics import collect_snapshot, is_fresh, preferred_addresses, read_throttle_flags, read_rail_voltages


class MetricsTests(unittest.TestCase):
    def test_prefers_physical_lan_and_handles_absent_network(self):
        self.assertEqual(preferred_addresses({"connectify0": ["198.51.100.2"],
                                              "wlan0": ["192.0.2.97", "192.0.2.98"],
                                              "lo": ["127.0.0.1"]}, {"wlan0"}),
                         ["192.0.2.97", "192.0.2.98"])
        self.assertEqual(preferred_addresses({}, set()), [])

    def test_failed_collectors_leave_unavailable_values(self):
        with patch("oled_panel.metrics.psutil.cpu_percent", side_effect=OSError), \
             patch("oled_panel.metrics.psutil.virtual_memory", side_effect=OSError), \
             patch("oled_panel.metrics.psutil.disk_usage", side_effect=OSError), \
             patch("oled_panel.metrics.psutil.net_if_addrs", side_effect=OSError), \
             patch("oled_panel.metrics.read_temperature", return_value=None):
            sample = collect_snapshot({"workload": None, "power": None})
        self.assertIsNone(sample["cpu_percent"])
        self.assertIsNone(sample["ram_available_bytes"])
        self.assertIsNone(sample["root_free_bytes"])
        self.assertEqual(sample["addresses"], [])
        self.assertIsNone(sample["temperature_c"])

    def test_ram_uses_available_field_and_missing_sensor_is_unknown(self):
        class Memory:
            available = 7 * 2**30
            total = 8 * 2**30
            free = 1 * 2**30
            used = 1 * 2**30
        with patch("oled_panel.metrics.psutil.virtual_memory", return_value=Memory()), \
             patch("oled_panel.metrics.read_temperature", return_value=None):
            sample = collect_snapshot({"workload": None, "power": None})
        self.assertEqual(sample["ram_available_bytes"], 7 * 2**30)
        self.assertIsNone(sample["temperature_c"])

    def test_stale_sample_is_not_fresh(self):
        self.assertTrue(is_fresh({"sampled_at": 10}, now=12))
        self.assertFalse(is_fresh({"sampled_at": 10}, now=14))
        self.assertFalse(is_fresh({"sampled_at": None}, now=14))

    def test_unknown_display_manager_does_not_claim_headless(self):
        with patch("oled_panel.metrics.subprocess.run", side_effect=OSError), \
             patch("oled_panel.metrics.read_temperature", return_value=None):
            sample = collect_snapshot({"display_manager": "lightdm", "workload": None, "power": None})
        self.assertIsNone(sample["current_mode"])

    def test_throttle_flags_distinguish_current_and_history(self):
        class Result:
            returncode = 0
            stdout = "throttled=0x10001\n"
        with patch("oled_panel.metrics.subprocess.run", return_value=Result()):
            flags = read_throttle_flags()
        self.assertTrue(flags["current"]["under_voltage"])
        self.assertTrue(flags["history"]["under_voltage"])
        self.assertFalse(flags["current"]["throttled"])
        self.assertFalse(flags["history"]["throttled"])
        with patch("oled_panel.metrics.subprocess.run", return_value=type("Clear", (), {"returncode": 0, "stdout": "throttled=0x0"})()):
            clear = read_throttle_flags()
        self.assertEqual(sum(clear["current"].values()) + sum(clear["history"].values()), 0)
        with patch("oled_panel.metrics.subprocess.run", side_effect=OSError):
            self.assertIsNone(read_throttle_flags())

    def test_snapshot_has_interface_load_used_and_supply_fields(self):
        sample = collect_snapshot({"workload": None, "power": None, "display_manager": None})
        for field in ("interfaces", "load_average", "ram_used_bytes", "root_used_bytes",
                      "root_total_bytes", "throttle_flags", "supply_warning", "rail_voltages"):
            self.assertIn(field, sample)
        self.assertIsInstance(sample["interfaces"], list)

    def test_pmic_voltages_are_labeled_and_fail_unavailable(self):
        output = "     EXT5V_V volt(24)=5.11344000V\n   3V3_SYS_V volt(9)=3.30910500V\n  VDD_CORE_V volt(15)=0.76422390V\n"
        with patch("oled_panel.metrics.subprocess.run", return_value=type("Result", (), {"returncode": 0, "stdout": output})()):
            rails = read_rail_voltages()
        self.assertEqual(rails, {"EXT5V_V": 5.11344, "3V3_SYS_V": 3.309105,
                                 "VDD_CORE_V": 0.7642239})
        with patch("oled_panel.metrics.subprocess.run", side_effect=OSError):
            self.assertIsNone(read_rail_voltages())


if __name__ == "__main__":
    unittest.main()

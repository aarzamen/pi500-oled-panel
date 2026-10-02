"""Read-only, failure-tolerant Linux telemetry collection."""
from __future__ import annotations

import ipaddress
from pathlib import Path
import re
import socket
import subprocess
import time
from urllib.request import urlopen

import psutil


def is_fresh(snapshot: dict, *, now: float | None = None, max_age: float = 3.0) -> bool:
    sampled = snapshot.get("sampled_at")
    now = time.time() if now is None else now
    return isinstance(sampled, (int, float)) and 0 <= now - sampled <= max_age


def preferred_addresses(by_interface: dict[str, list[str]], active: set[str]) -> list[str]:
    """Prefer active Ethernet/Wi-Fi LAN IPv4, then other active non-loopback IPs."""
    def rank(name: str):
        if name.startswith(("eth", "en")):
            return 0
        if name.startswith(("wlan", "wl")):
            return 1
        return 2
    result = []
    for name in sorted(active, key=lambda item: (rank(item), item)):
        for address in by_interface.get(name, []):
            try:
                parsed = ipaddress.ip_address(address.split("%", 1)[0])
            except ValueError:
                continue
            if parsed.is_loopback or parsed.is_link_local or parsed.is_unspecified:
                continue
            result.append((rank(name), parsed.version, address))
    result.sort(key=lambda item: (item[0], item[1]))
    return list(dict.fromkeys(address for _, _, address in result))


def read_temperature() -> float | None:
    for path in sorted(Path("/sys/class/thermal").glob("thermal_zone*/temp")):
        try:
            value = float(path.read_text().strip()) / 1000.0
            if -20 <= value <= 150:
                return value
        except (OSError, ValueError):
            continue
    try:
        sensors = psutil.sensors_temperatures()
        for entries in sensors.values():
            for entry in entries:
                if -20 <= entry.current <= 150:
                    return float(entry.current)
    except (OSError, AttributeError, ValueError):
        pass
    return None


THROTTLE_BITS = (("under_voltage", 0), ("frequency_capped", 1),
                 ("throttled", 2), ("soft_temp_limit", 3))


def read_throttle_flags() -> dict | None:
    """Decode Pi vcgencmd's current bits 0-3 and historical bits 16-19."""
    try:
        result = subprocess.run(["/usr/bin/vcgencmd", "get_throttled"],
                                capture_output=True, text=True, timeout=0.4, check=False)
        match = re.fullmatch(r"throttled=0x([0-9a-fA-F]+)", result.stdout.strip())
        if result.returncode != 0 or match is None:
            return None
        value = int(match.group(1), 16)
        return {"current": {name: bool(value & (1 << bit)) for name, bit in THROTTLE_BITS},
                "history": {name: bool(value & (1 << (bit + 16))) for name, bit in THROTTLE_BITS}}
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return None


RAIL_NAMES = ("EXT5V_V", "3V3_SYS_V", "VDD_CORE_V")


def read_rail_voltages() -> dict[str, float] | None:
    """Read labeled Pi PMIC voltages; never infer input power from them."""
    try:
        result = subprocess.run(["/usr/bin/vcgencmd", "pmic_read_adc"],
                                capture_output=True, text=True, timeout=0.4, check=False)
        if result.returncode != 0:
            return None
        rails = {}
        for name, value in re.findall(r"^[ \t]*([A-Z0-9_]+) volt\(\d+\)=([0-9.]+)V[ \t]*$",
                                      result.stdout, re.MULTILINE):
            if name in RAIL_NAMES:
                number = float(value)
                if 0 <= number < 20:
                    rails[name] = number
        return rails or None
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return None


def _supply_warning(flags: dict | None) -> str | None:
    if flags is None:
        return None
    if flags["current"]["under_voltage"]:
        return "Undervoltage now"
    if flags["history"]["under_voltage"]:
        return "Past undervoltage"
    return "No undervoltage flags"


def _read_power(config: dict | None) -> tuple[float | None, str | None]:
    if not config:
        return None, None
    try:
        value = float(Path(config["path"]).read_text().strip()) * config["scale"]
        if 0 <= value < 1000:
            return value, config["scope"]
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return None, config.get("scope")


def _workload_state(config: dict | None) -> str:
    if not config:
        return "Not configured"
    try:
        if config["type"] == "service":
            result = subprocess.run(["systemctl", "is-active", config["name"]],
                                    capture_output=True, text=True, timeout=0.4, check=False)
            value = result.stdout.strip()
            return "Ready" if result.returncode == 0 and value == "active" else \
                   ("Stopped" if value in {"inactive", "failed"} else "unavailable")
        with urlopen(config["url"], timeout=0.4) as response:
            return "Ready" if 200 <= response.status < 400 else "unavailable"
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired, TimeoutError):
        return "unavailable"


from .runtime import runtime_values


def collect_snapshot(config: dict) -> dict:
    """Return one timestamped sample; each unavailable reading is independent."""
    config = {**config, **runtime_values()}
    sample = {"sampled_at": time.time(), "hostname": None, "addresses": [],
              "interfaces": [], "load_average": None, "ram_used_bytes": None,
              "cpu_percent": None, "ram_available_bytes": None, "ram_total_bytes": None,
              "temperature_c": None, "throttle_flags": None, "supply_warning": None,
              "rail_voltages": None,
              "root_free_bytes": None, "root_used_bytes": None, "root_total_bytes": None,
              "uptime_s": None,
              "power_watts": None, "power_scope": None, "workload_state": "Not configured",
              "current_mode": None, "one_time_mode": config.get("one_time_mode"),
              "boot_default": config.get("boot_default", "Desktop")}
    try:
        sample["hostname"] = socket.gethostname()
    except OSError:
        pass
    try:
        addresses = {name: [item.address for item in values if item.family in (socket.AF_INET, socket.AF_INET6)]
                     for name, values in psutil.net_if_addrs().items()}
        stats = psutil.net_if_stats()
        active = {name for name, item in stats.items() if item.isup}
        sample["addresses"] = preferred_addresses(addresses, active)
        sample["interfaces"] = [{"name": name,
                                  "link_state": ("up" if stats[name].isup else "down") if name in stats else "unavailable",
                                  "addresses": values}
                                 for name, values in sorted(addresses.items())]
    except (OSError, ValueError):
        pass
    try:
        sample["cpu_percent"] = psutil.cpu_percent(interval=0.1)
    except (OSError, ValueError):
        pass
    try:
        sample["load_average"] = list(psutil.getloadavg())
    except (OSError, AttributeError, ValueError):
        pass
    try:
        memory = psutil.virtual_memory()
        sample["ram_used_bytes"] = memory.used
        sample["ram_available_bytes"] = memory.available
        sample["ram_total_bytes"] = memory.total
    except (OSError, ValueError):
        pass
    sample["temperature_c"] = read_temperature()
    sample["throttle_flags"] = read_throttle_flags()
    sample["supply_warning"] = _supply_warning(sample["throttle_flags"])
    sample["rail_voltages"] = read_rail_voltages()
    try:
        disk = psutil.disk_usage("/")
        sample["root_free_bytes"] = disk.free
        sample["root_used_bytes"] = disk.used
        sample["root_total_bytes"] = disk.total
    except (OSError, ValueError):
        pass
    try:
        sample["uptime_s"] = max(0, sample["sampled_at"] - psutil.boot_time())
    except (OSError, ValueError):
        pass
    sample["power_watts"], sample["power_scope"] = _read_power(config.get("power"))
    sample["workload_state"] = _workload_state(config.get("workload"))
    manager = config.get("display_manager", "lightdm")
    if manager:
        try:
            result = subprocess.run(["systemctl", "is-active", manager], capture_output=True,
                                    text=True, timeout=0.4, check=False)
            value = result.stdout.strip()
            if result.returncode == 0 and value == "active":
                sample["current_mode"] = "Desktop"
            elif value in {"inactive", "failed"}:
                sample["current_mode"] = "Headless"
        except (OSError, subprocess.TimeoutExpired):
            pass
    return sample

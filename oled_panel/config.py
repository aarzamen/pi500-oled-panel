"""Validated device settings; loading never changes system state."""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse


DEFAULT = {"bus": 1, "address": 60, "keys": True, "polarity": "low",
           "gpiochip": 0, "pins": [17, 27, 22, 23], "rotate": 0,
           "display_manager": "lightdm", "boot_default": "Desktop",
           "workload": None, "power": None}


def load_config(path: str | Path | None) -> dict:
    supplied = json.loads(Path(path).read_text()) if path is not None else {}
    if not isinstance(supplied, dict):
        raise ValueError("configuration must be a JSON object")
    unknown = set(supplied) - set(DEFAULT)
    if unknown:
        raise ValueError(f"unknown configuration keys: {', '.join(sorted(unknown))}")
    config = {**DEFAULT, **supplied}
    for key in ("bus", "gpiochip"):
        if type(config[key]) is not int or config[key] < 0:
            raise ValueError(f"{key} must be a nonnegative integer")
    if type(config["address"]) is not int or config["address"] not in (60, 61):
        raise ValueError("address must be decimal 60 or 61 (0x3c or 0x3d)")
    if type(config["keys"]) is not bool:
        raise ValueError("keys must be boolean")
    if config["polarity"] not in ("low", "high"):
        raise ValueError("polarity must be low or high")
    pins = config["pins"]
    if not isinstance(pins, list) or len(pins) != 4 or any(type(p) is not int or p < 4 or p > 27 for p in pins) or len(set(pins)) != 4:
        raise ValueError("pins must be four distinct GPIO numbers from 4 to 27")
    if config["rotate"] not in (0, 2):
        raise ValueError("rotate must be 0 or 2")
    if config["boot_default"] not in ("Desktop", "Headless"):
        raise ValueError("boot_default must be Desktop or Headless")
    manager = config["display_manager"]
    if manager is not None and (not isinstance(manager, str) or not manager or
                                any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@_.-" for c in manager)):
        raise ValueError("display_manager must be a systemd unit name or null")
    workload = config["workload"]
    if workload is not None:
        if not isinstance(workload, dict) or workload.get("type") not in ("service", "endpoint"):
            raise ValueError("workload must specify service or endpoint")
        if workload["type"] == "service":
            name = workload.get("name")
            if not isinstance(name, str) or not name.endswith(".service") or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@_.-" for c in name):
                raise ValueError("workload service needs a valid .service name")
        else:
            url = workload.get("url")
            parsed = urlparse(url) if isinstance(url, str) else None
            if parsed is None or parsed.scheme not in ("http", "https") or not parsed.netloc:
                raise ValueError("workload endpoint needs an http(s) URL")
    power = config["power"]
    if power is not None:
        if not isinstance(power, dict) or not isinstance(power.get("path"), str) or \
                not power["path"].startswith("/sys/") or not isinstance(power.get("scope"), str) or \
                not power["scope"].strip() or power["scope"].lower() == "total input" or \
                not isinstance(power.get("scale"), (int, float)) or power["scale"] <= 0:
            raise ValueError("power requires a /sys/ path, positive scale, and labeled rail scope")
    return config

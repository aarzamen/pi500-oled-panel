"""Pi OLED dashboard with dry-run foreground and installed action modes."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from queue import Empty, Queue
from threading import Thread
import sys
import signal
import subprocess
import time

from hardware_check import PanelHardware

from .config import load_config
from .metrics import collect_snapshot
from .ui import PAGES, initial_state, render_ui, update_ui


class KeyEdges:
    """Turn physical key sets into edges; startup-held keys have no down edge."""
    def __init__(self, initial: set[str]):
        self.previous = set(initial)

    def events(self, current: set[str]) -> list[dict]:
        current = set(current)
        events = [{"type": "key_up", "key": key} for key in sorted(self.previous - current)]
        events += [{"type": "key_down", "key": key} for key in sorted(current - self.previous)]
        self.previous = current
        return events


def _sample_loop(config: dict, samples: Queue, stop: list[bool]) -> None:
    """Daemon sampler isolates slow or failed collectors from 50 Hz input polling."""
    next_at = time.monotonic()
    while not stop[0]:
        if time.monotonic() >= next_at:
            try:
                samples.put_nowait(collect_snapshot(config))
            except Exception as error:
                print(f"Metrics sample failed: {error}", file=sys.stderr, flush=True)
            next_at = time.monotonic() + 1.0
        time.sleep(0.05)


def dispatch_action(action: str) -> None:
    allowed = {'start-desktop', 'stop-desktop', 'reboot', 'shutdown',
               'set-default desktop', 'set-default headless'}
    if action not in allowed:
        raise ValueError('unsupported panel action')
    result = subprocess.run(['/usr/bin/sudo', '-n', '/usr/local/libexec/oled-panel-action',
                             *action.split(' ')], capture_output=True, text=True, timeout=3)
    if result.returncode:
        raise RuntimeError((result.stderr.strip() or 'action helper rejected request')[-240:])


def perform_action(state, action, dispatch=None):
    if dispatch is None:
        print(f'DRY RUN action: {action}', flush=True)
        return
    try:
        dispatch(action)
        print(f'Action accepted: {action}', flush=True)
    except Exception as error:
        state.view = 'action-error'
        state.action_error = str(error)
        state.blank = False
        state.last_input = time.monotonic()
        print(f'Action failed ({action}): {error}', file=sys.stderr, flush=True)


def run_foreground(panel, config: dict, *, seconds: float | None, dispatch=None,
                   stopped=lambda: False) -> None:
    """Poll keys and render; dispatch is absent for a harmless foreground dry run."""
    stop = [False]
    samples: Queue = Queue(maxsize=2)
    sampler = Thread(target=_sample_loop, args=(config, samples, stop), daemon=True)
    start = time.monotonic()
    state = initial_state(now=start, boot_default=config["boot_default"])
    snapshot = {}
    old_frame = None
    try:
        edges = KeyEdges(panel.read_keys())
        sampler.start()
        while not stopped() and (seconds is None or time.monotonic() - start < seconds):
            now = time.monotonic()
            try:
                while True:
                    snapshot = samples.get_nowait()
                    state, _ = update_ui(state, {"type": "snapshot", "snapshot": snapshot}, now)
            except Empty:
                pass
            for event in edges.events(panel.read_keys()):
                state, action = update_ui(state, event, now)
                if action is not None:
                    perform_action(state, action, dispatch)
            state, action = update_ui(state, {"type": "tick"}, now)
            if action is not None:
                perform_action(state, action, dispatch)
            frame = render_ui(state, snapshot)
            encoded = frame.tobytes()
            if encoded != old_frame:
                panel.show(frame)
                old_frame = encoded
            time.sleep(0.02)
    finally:
        stop[0] = True
        panel.close()


def _preview(directory: Path, config: dict) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    sample = {"sampled_at": time.time(), "hostname": "pi500", "addresses": ["192.0.2.97", "192.0.2.98"],
              "interfaces": [{"name": "eth0", "link_state": "down", "addresses": []},
                             {"name": "wlan0", "link_state": "up", "addresses": ["192.0.2.97", "192.0.2.98"]}],
              "cpu_percent": 17.5, "ram_available_bytes": 7 * 2**30,
              "ram_used_bytes": 1 * 2**30, "ram_total_bytes": 8 * 2**30,
              "load_average": [1.1, 0.9, 0.8], "temperature_c": 43.2,
              "throttle_flags": {"current": {"under_voltage": False, "frequency_capped": False,
                                              "throttled": False, "soft_temp_limit": False},
                                 "history": {"under_voltage": False, "frequency_capped": False,
                                             "throttled": False, "soft_temp_limit": False}},
              "supply_warning": "No undervoltage flags",
              "rail_voltages": {"EXT5V_V": 5.11344, "3V3_SYS_V": 3.309105, "VDD_CORE_V": 0.7642239},
              "root_free_bytes": 13 * 2**30, "root_used_bytes": 16 * 2**30,
              "root_total_bytes": 29 * 2**30, "uptime_s": 7200,
              "power_watts": None, "power_scope": None, "workload_state": "Not configured"}
    for page, name in enumerate(PAGES):
        state = initial_state(now=time.monotonic(), current_mode="Desktop",
                              boot_default=config["boot_default"])
        state.page = page
        target = directory / f"{page + 1}-{name.lower()}.png"
        render_ui(state, sample).save(target)
        print(f"Saved {target.resolve()} (software preview)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--daemon", action="store_true", help="installed nonroot daemon with real actions")
    mode.add_argument("--foreground", action="store_true", help="run on the verified Pi display")
    mode.add_argument("--preview-dir", type=Path, help="save seven software frames without hardware")
    mode.add_argument("--snapshot", action="store_true", help="print read-only metrics JSON without hardware")
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--dry-run-actions", action="store_true", help="log action names only")
    actions.add_argument("--real-actions", action="store_true", help="explicitly enable installed helper in foreground")
    parser.add_argument("--config", type=Path, help="validated JSON device configuration")
    parser.add_argument("--seconds", type=float, default=60.0, help="foreground duration (1 to 300 seconds)")
    args = parser.parse_args(argv)
    if args.foreground and not (args.dry_run_actions or args.real_actions):
        parser.error("--foreground requires --dry-run-actions or --real-actions")
    if args.foreground and not 0 < args.seconds <= 300:
        parser.error("--seconds must be greater than 0 and at most 300")
    try:
        config = load_config(args.config)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        parser.error(f"invalid config: {error}")
    if args.preview_dir:
        _preview(args.preview_dir, config)
        return 0
    if args.snapshot:
        print(json.dumps(collect_snapshot(config), indent=2, sort_keys=True))
        return 0
    hardware_args = argparse.Namespace(bus=config["bus"], address=config["address"],
                                       keys=config["keys"], polarity=config["polarity"],
                                       gpiochip=config["gpiochip"], pins=config["pins"],
                                       rotate=config["rotate"])
    stop_requested = [False]
    old_term = signal.getsignal(signal.SIGTERM)
    signal.signal(signal.SIGTERM, lambda *_: stop_requested.__setitem__(0, True))
    try:
        run_foreground(PanelHardware(hardware_args), config,
                       seconds=None if args.daemon else args.seconds,
                       dispatch=dispatch_action if not args.dry_run_actions else None,
                       stopped=lambda: stop_requested[0])
    except KeyboardInterrupt:
        print("Stopped.")
    except Exception as error:
        print(f"Dashboard failed: {error}", file=sys.stderr)
        return 1
    finally:
        signal.signal(signal.SIGTERM, old_term)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

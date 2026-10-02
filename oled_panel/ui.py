"""Pure dashboard state transitions and 128x64 one-bit rendering."""
from __future__ import annotations

from dataclasses import dataclass, field
import time

from PIL import Image, ImageDraw, ImageFont


PAGES = ("Home", "Network", "Compute", "Thermal", "Power", "Storage", "Workload")
MENU = (("Start Desktop", "start-desktop"), ("Stop Desktop", "stop-desktop"),
        ("Reboot", "reboot"), ("Shutdown", "shutdown"),
        ("Boot Default", None))
IDLE_SECONDS = 60.0
HOLD_SECONDS = 2.0


@dataclass
class UIState:
    page: int = 0
    view: str = "page"
    detail_index: int = 0
    snapshot: dict = field(default_factory=dict)
    menu_index: int = 0
    default_index: int = 0
    blank: bool = False
    last_input: float = 0.0
    wake_suppressed: set[str] = field(default_factory=set)
    held_keys: set[str] = field(default_factory=set)
    wake_active: bool = False
    confirm_action: str | None = None
    select_wait_release: bool = False
    select_started: float | None = None
    action_sent: bool = False
    current_mode: str | None = None
    one_time_mode: str | None = None
    boot_default: str | None = "Desktop"
    action_error: str = ""


def initial_state(*, now: float = 0.0, current_mode: str | None = None,
                  boot_default: str | None = "Desktop") -> UIState:
    return UIState(last_input=now, current_mode=current_mode, boot_default=boot_default)


def update_ui(state: UIState, event: dict, now: float) -> tuple[UIState, str | None]:
    """Apply semantic key edges, ticks, or a snapshot; return a dry-run action name."""
    kind = event.get("type")
    key = event.get("key")
    if kind == "snapshot":
        snapshot = event.get("snapshot") or {}
        state.snapshot = snapshot
        state.current_mode = snapshot.get("current_mode", state.current_mode)
        state.one_time_mode = snapshot.get("one_time_mode", state.one_time_mode)
        state.boot_default = snapshot.get("boot_default", state.boot_default)
        return state, None
    if kind == "tick":
        if state.view == "confirm" and state.select_started is not None \
                and not state.action_sent and now - state.select_started >= HOLD_SECONDS:
            state.action_sent = True
            action = state.confirm_action
            state.select_started = None
            state.view = "page"
            return state, action
        if now - state.last_input >= IDLE_SECONDS:
            state.blank = True
        return state, None
    if kind not in {"key_down", "key_up"} or key not in {"up", "down", "select", "back"}:
        return state, None
    if kind == "key_up":
        state.held_keys.discard(key)
        state.wake_suppressed.discard(key)
        if not state.held_keys:
            state.wake_active = False
        if key == "select":
            state.select_wait_release = False
            state.select_started = None
        return state, None
    state.last_input = now
    state.held_keys.add(key)
    if state.blank:
        state.blank = False
        state.wake_active = True
        state.wake_suppressed.add(key)
        return state, None
    if state.wake_active:
        state.wake_suppressed.add(key)
        return state, None
    if state.view == "action-error":
        state.blank = False
        if key == "back":
            state.view = "page"
            state.action_error = ""
        return state, None
    if state.view == "confirm":
        if key == "back":
            state.view = "menu" if not (state.confirm_action or "").startswith("set-default") else "default"
            state.confirm_action = None
            state.select_started = None
        elif key == "select" and not state.select_wait_release:
            state.select_started = now
        return state, None
    if state.view == "detail":
        if key == "back":
            state.view = "page"
        elif key == "select":
            state.detail_index = (state.detail_index + 1) % len(detail_pages(state, state.snapshot))
        elif key in {"up", "down"}:
            state.page = (state.page + (-1 if key == "up" else 1)) % len(PAGES)
            state.view = "page"
        return state, None
    if state.view == "default":
        if key == "back":
            state.view = "menu"
        elif key in {"up", "down"}:
            state.default_index = 1 - state.default_index
        elif key == "select":
            state.confirm_action = "set-default " + ("desktop", "headless")[state.default_index]
            state.view = "confirm"
            state.select_wait_release = True
            state.action_sent = False
        return state, None
    if state.view == "menu":
        if key == "back":
            state.view = "page"
        elif key == "up":
            state.menu_index = (state.menu_index - 1) % len(MENU)
        elif key == "down":
            state.menu_index = (state.menu_index + 1) % len(MENU)
        elif key == "select":
            action = MENU[state.menu_index][1]
            if action is None:
                state.view = "default"
            else:
                state.confirm_action = action
                state.view = "confirm"
                state.select_wait_release = True
                state.action_sent = False
        return state, None
    if key == "back":
        state.view = "menu"
    elif key == "select":
        state.view = "detail"
        state.detail_index = 0
    elif key == "up":
        state.page = (state.page - 1) % len(PAGES)
    elif key == "down":
        state.page = (state.page + 1) % len(PAGES)
    return state, None


def _fmt(value, format_spec=""):
    return "unavailable" if value is None else format(value, format_spec)


def _gib(value):
    return "unavailable" if value is None else f"{value / 2**30:.1f}GiB"


def _fit(draw, text: str, font, width=124):
    text = str(text)
    while text and draw.textlength(text, font=font) > width:
        text = text[:-1]
    return text


def _wrap_pixels(text: str, *, width: int = 124) -> list[str]:
    font = ImageFont.load_default(size=9)
    draw = ImageDraw.Draw(Image.new("1", (128, 64)))
    chunks: list[str] = []
    chunk = ""
    for char in text:
        if chunk and draw.textlength(chunk + char, font=font) > width:
            chunks.append(chunk)
            chunk = char
        else:
            chunk += char
    chunks.append(chunk)
    return chunks


def _value(value, *, unit="", digits=1):
    return "unavailable" if value is None else f"{value:.{digits}f}{unit}"


def _hours(value):
    return "unavailable" if value is None else f"{int(value // 3600)}h"


def _flag_summary(flags: dict | None, period: str) -> str:
    if flags is None:
        return "unavailable"
    abbreviations = (("under_voltage", "UV"), ("frequency_capped", "CAP"),
                     ("throttled", "THR"), ("soft_temp_limit", "TEMP"))
    active = [short for name, short in abbreviations if flags.get(period, {}).get(name)]
    return ",".join(active) if active else "clear"


def _detail_fields(state: UIState, sample: dict) -> list[tuple[str, str]]:
    page = state.page
    if page == 0:
        return [("Hostname", sample.get("hostname") or "unavailable"),
                ("Best address", (sample.get("addresses") or ["unavailable"])[0]),
                ("Current mode", state.current_mode or "unavailable"),
                ("One-time mode", state.one_time_mode or "unavailable"),
                ("Saved default", state.boot_default or "unavailable"),
                ("CPU", _value(sample.get("cpu_percent"), unit="%")),
                ("RAM available", _gib(sample.get("ram_available_bytes"))),
                ("Temperature", _value(sample.get("temperature_c"), unit=" C")),
                ("Application", sample.get("workload_state") or "unavailable")]
    if page == 1:
        fields = []
        for interface in sample.get("interfaces") or []:
            name = interface.get("name") or "unknown"
            fields.append((f"{name} link", interface.get("link_state") or "unavailable"))
            for index, address in enumerate(interface.get("addresses") or ["unavailable"], 1):
                fields.append((f"{name} IP {index}", address))
        return fields or [("Interfaces", "unavailable")]
    if page == 2:
        load = sample.get("load_average")
        return [("CPU", _value(sample.get("cpu_percent"), unit="%")),
                ("Load 1/5/15", ", ".join(f"{part:.2f}" for part in load) if load else "unavailable"),
                ("RAM used", _gib(sample.get("ram_used_bytes"))),
                ("RAM available", _gib(sample.get("ram_available_bytes"))),
                ("RAM total", _gib(sample.get("ram_total_bytes")))]
    if page == 3:
        flags = sample.get("throttle_flags")
        fields = [("SoC temperature", _value(sample.get("temperature_c"), unit=" C"))]
        for period in ("current", "history"):
            for name, _ in THERMAL_FLAGS:
                value = "unavailable" if flags is None else ("yes" if flags.get(period, {}).get(name) else "no")
                fields.append((f"{period} {name.replace('_', ' ')}", value))
        return fields
    if page == 4:
        fields = [("Total input watts", "unavailable"),
                ("Supply warning", sample.get("supply_warning") or "unavailable"),
                ("Rail watts", _value(sample.get("power_watts"), unit=" W", digits=2)),
                ("Rail scope", sample.get("power_scope") or "unavailable")]
        for name in ("EXT5V_V", "3V3_SYS_V", "VDD_CORE_V"):
            volts = (sample.get("rail_voltages") or {}).get(name)
            fields.append((name, _value(volts, unit=" V", digits=3)))
        return fields
    if page == 5:
        return [("Root used", _gib(sample.get("root_used_bytes"))),
                ("Root free", _gib(sample.get("root_free_bytes"))),
                ("Root total", _gib(sample.get("root_total_bytes"))),
                ("Uptime", _hours(sample.get("uptime_s")))]
    return [("Application state", sample.get("workload_state") or "unavailable")]


THERMAL_FLAGS = (("under_voltage", "Undervoltage"), ("frequency_capped", "Frequency capped"),
                 ("throttled", "Throttled"), ("soft_temp_limit", "Soft temp limit"))


def detail_pages(state: UIState, snapshot: dict) -> list[tuple[str, list[str]]]:
    """Wrap every field into five-line pages so complete values are reachable."""
    if not snapshot or not is_render_fresh(snapshot):
        return [("", ["Telemetry unavailable"])]
    pages = []
    for label, value in _detail_fields(state, snapshot):
        lines = _wrap_pixels(f"{label}: {value}")
        for offset in range(0, len(lines), 5):
            pages.append((label, lines[offset:offset + 5]))
    return pages or [("", ["No details available"])]


def _lines(state: UIState, sample: dict) -> list[str]:
    if state.view == "action-error":
        return ["Action failed"] + _wrap_pixels(state.action_error)[:3] + ["K4 dismiss / see journal"]
    if state.view == "menu":
        return [f"{'>' if index == state.menu_index else ' '}{label}"
                for index, (label, _) in enumerate(MENU)]
    if state.view == "default":
        return ["Saved boot default:",
                f"{'>' if state.default_index == 0 else ' '}Desktop",
                f"{'>' if state.default_index == 1 else ' '}Headless",
                "K3 select / K4 back"]
    if state.view == "confirm":
        label = (state.confirm_action or "").replace("-", " ").title()
        return [label, "Hold K3 Select 2s", "K4 Cancel",
                "Ends graphical apps" if state.confirm_action == "stop-desktop" else "No action until held"]
    if state.view == "detail":
        pages = detail_pages(state, sample)
        return pages[state.detail_index % len(pages)][1]
    if not sample or not is_render_fresh(sample):
        return ["Telemetry unavailable", "Waiting for fresh sample", "K4 actions"]
    addr = (sample.get("addresses") or ["unavailable"])[0]
    page = state.page
    if page == 0:
        cpu = sample.get("cpu_percent")
        ram = sample.get("ram_available_bytes")
        temp = sample.get("temperature_c")
        return [f"Host {sample.get('hostname') or 'unavailable'}", f"IP {addr}",
                f"Mode {state.current_mode or 'unavailable'}",
                f"CPU {round(cpu) if cpu is not None else 'N/A'}% R{ram / 2**30:.1f}G T{round(temp)}C"
                if ram is not None and temp is not None else f"CPU {_fmt(cpu, '.0f')}% RAM {_gib(ram)} T{_fmt(temp, '.0f')}C",
                f"App {sample.get('workload_state') or 'unavailable'}"]
    if page == 1:
        interfaces = sample.get("interfaces") or []
        lines = [f"{item.get('name', '?')} {item.get('link_state', '?')} " +
                 (item.get("addresses") or ["no IP"])[0] for item in interfaces[:4]]
        return lines + ["K3 all interfaces/IPs"] if lines else ["No interfaces available", "K3 details"]
    if page == 2:
        load = sample.get("load_average")
        return [f"CPU {_fmt(sample.get('cpu_percent'), '.1f')}% Load {_fmt(load[0], '.1f') if load else 'N/A'}",
                f"RAM used {_gib(sample.get('ram_used_bytes'))}",
                f"RAM avail {_gib(sample.get('ram_available_bytes'))}",
                f"RAM total {_gib(sample.get('ram_total_bytes'))}", "K3 load details"]
    if page == 3:
        flags = sample.get("throttle_flags")
        return [f"SoC {_value(sample.get('temperature_c'), unit=' C')}",
                f"Now {_flag_summary(flags, 'current')}",
                f"History {_flag_summary(flags, 'history')}", "K3 individual flags"]
    if page == 4:
        rails = sample.get("rail_voltages") or {}
        return ["Total input: unavailable", f"Supply {sample.get('supply_warning') or 'unavailable'}",
                f"EXT5V {_value(rails.get('EXT5V_V'), unit='V', digits=2)}",
                f"3V3 {_value(rails.get('3V3_SYS_V'), unit='V', digits=2)}",
                f"Core {_value(rails.get('VDD_CORE_V'), unit='V', digits=2)}"]
    if page == 5:
        return ["Root filesystem", f"Used {_gib(sample.get('root_used_bytes'))}",
                f"Free {_gib(sample.get('root_free_bytes'))}",
                f"Uptime {_hours(sample.get('uptime_s'))}"]
    return ["Application monitor", sample.get("workload_state") or "unavailable"]


def is_render_fresh(sample: dict, *, now: float | None = None) -> bool:
    timestamp = sample.get("sampled_at")
    now = time.time() if now is None else now
    return isinstance(timestamp, (int, float)) and 0 <= now - timestamp <= 3.0


def render_ui(state: UIState, snapshot: dict) -> Image.Image:
    image = Image.new("1", (128, 64), 0)
    if state.blank:
        return image
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=9)
    title = PAGES[state.page] if state.view in {"page", "detail"} else state.view.title()
    indicator = None
    if state.view == "page":
        indicator = f"{state.page + 1}/7"
    elif state.view == "detail":
        indicator = f"{state.detail_index % len(detail_pages(state, snapshot)) + 1}/{len(detail_pages(state, snapshot))}"
    if indicator:
        left = 126 - draw.textlength(indicator, font=font)
        draw.text((left, 2), indicator, font=font, fill=1)
        draw.text((2, 2), _fit(draw, title, font, width=left - 5), font=font, fill=1)
    else:
        draw.text((2, 2), _fit(draw, title, font), font=font, fill=1)
    draw.line((0, 15, 127, 15), fill=1)
    for row, line in enumerate(_lines(state, snapshot)[:5]):
        draw.text((2, 17 + row * 9), _fit(draw, line, font), font=font, fill=1)
    return image

"""Read installed defaults and this boot's choice without changing system state."""
import json
from pathlib import Path
import re

from .config import INTEGRATED_BOOT_LABELS


def read_boot_id():
    with Path('/proc/sys/kernel/random/boot_id').open(encoding='ascii') as stream:
        raw = stream.read(65)
    value = raw.strip()
    if len(raw) > 64 or not re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', value):
        raise ValueError('current boot identity unavailable')
    return value


def runtime_values(etc=Path('/etc/oled-panel'), runtime=Path('/run/oled-panel')):
    if not etc.exists():
        return {}
    values = {'display_manager': None, 'boot_default': None, 'one_time_mode': None}
    integrated = False
    try:
        device = json.loads((etc / 'device.json').read_text())
        integrated = isinstance(device, dict) and device.get('panelbridge') is True
    except (OSError, ValueError): pass
    modes = ('wireless', 'desktop', 'headless') if integrated else ('desktop', 'headless')
    try:
        manager = json.loads((etc / 'actions.json').read_text())['display_manager']
        if isinstance(manager, str) and re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.@-]*\.service', manager):
            values['display_manager'] = manager
    except (OSError, ValueError, KeyError, TypeError): pass
    try:
        default = (etc / 'default').read_text().strip()
        if default in modes: values['boot_default'] = default.title()
    except OSError: pass
    try:
        choice = json.loads((runtime / 'choice.json').read_text())
        mode = choice['mode']
        if integrated:
            if choice.get('panelbridge') is True and choice.get('boot_id') == read_boot_id() and mode in modes:
                values['one_time_mode'] = INTEGRATED_BOOT_LABELS[mode]
        elif mode in modes and 'panelbridge' not in choice:
            values['one_time_mode'] = mode.title()
    except (OSError, ValueError, KeyError, TypeError): pass
    return values

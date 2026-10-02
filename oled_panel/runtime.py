"""Read installed defaults and this boot's choice without changing system state."""
import json
from pathlib import Path
import re


def runtime_values(etc=Path('/etc/oled-panel'), runtime=Path('/run/oled-panel')):
    if not etc.exists():
        return {}
    values = {'display_manager': None, 'boot_default': None, 'one_time_mode': None}
    try:
        manager = json.loads((etc / 'actions.json').read_text())['display_manager']
        if isinstance(manager, str) and re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.@-]*\.service', manager):
            values['display_manager'] = manager
    except (OSError, ValueError, KeyError, TypeError): pass
    try:
        default = (etc / 'default').read_text().strip()
        if default in ('desktop', 'headless'): values['boot_default'] = default.title()
    except OSError: pass
    try:
        choice = json.loads((runtime / 'choice.json').read_text())['mode']
        if choice in ('desktop', 'headless'): values['one_time_mode'] = choice.title()
    except (OSError, ValueError, KeyError, TypeError): pass
    return values

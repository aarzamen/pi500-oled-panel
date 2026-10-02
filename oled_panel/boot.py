"""Bounded boot selection. Exceptions always fall back to Desktop."""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import time

from PIL import Image, ImageDraw, ImageFont
from hardware_check import PanelHardware
from .config import INTEGRATED_BOOT_LABELS, load_config
from .runtime import read_boot_id

RUNTIME = Path('/run/oled-panel')


def load_splash():
    """Reuse the Tracker's original 128x64 pixels without scaling or cropping."""
    with Image.open(Path(__file__).with_name('assets') / 'george-startup.png') as source:
        if source.size != (128, 64):
            raise ValueError('startup artwork must be 128x64')
        return source.convert('1')


def clear_choice(runtime: Path) -> None:
    for name in ('headless', 'choice.json'):
        (runtime / name).unlink(missing_ok=True)


def atomic_write(path: Path, data: str) -> None:
    fd, temporary = tempfile.mkstemp(prefix='.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def render_choice(selected: str, remaining: float, *, navigating: bool, panelbridge=False):
    image = Image.new('1', (128, 64))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=9)
    draw.text((2, 2), 'STARTUP', font=font, fill=1)
    draw.line((0, 15, 127, 15), fill=1)
    if panelbridge:
        lines = [f"{'>' if selected == mode else ' '} {label}"
                 for mode, label in INTEGRATED_BOOT_LABELS.items()]
        lines += ['K1/K2 choose K3 OK', f'K4 default {math.ceil(remaining)}s']
    else:
        lines = [f"{'>' if selected == 'desktop' else ' '} Desktop",
                 f"{'>' if selected == 'headless' else ' '} Headless (this boot)",
                 'K1/K2 choose K3 OK', 'K4 saved default',
                 f"Default in {math.ceil(remaining)}s"]
    for row, line in enumerate(lines):
        draw.text((2, 17 + row * 9), line, font=font, fill=1)
    return image


def choose_boot_mode(config, hardware, clock=time) -> str:
    """hardware is a lazy factory so initialization is inside the failure boundary."""
    runtime = Path(config.get('runtime_dir', RUNTIME))
    panel = None
    mode = 'desktop'
    try:
        clear_choice(runtime)
        integrated = config.get('panelbridge', False)
        if type(integrated) is not bool:
            raise ValueError('invalid integration setting')
        modes = ('wireless', 'desktop', 'headless') if integrated else ('desktop', 'headless')
        default = config['boot_default'].lower()
        if default not in modes:
            raise ValueError('invalid saved default')
        start = clock.monotonic()
        panel = hardware()
        try:
            splash = load_splash()
        except (OSError, ValueError) as error:
            print(f'Startup artwork unavailable: {error}', file=sys.stderr, flush=True)
        else:
            panel.show(splash)
            clock.sleep(min(2.0, max(0.0, 30 - (clock.monotonic() - start))))
        chooser_start = clock.monotonic()
        previous = set(panel.read_keys())
        selected = default
        navigating = False
        while True:
            elapsed = clock.monotonic() - start
            chooser_elapsed = clock.monotonic() - chooser_start
            if elapsed >= 30 or (not navigating and chooser_elapsed >= 8):
                mode = default
                break
            current = set(panel.read_keys())
            pressed = current - previous
            previous = current
            if 'back' in pressed:
                mode = default
                break
            if 'up' in pressed or 'down' in pressed:
                direction = -1 if 'up' in pressed else 1
                selected = modes[(modes.index(selected) + direction) % len(modes)]
                navigating = True
            # A chord cannot accidentally confirm the selection it just changed.
            elif pressed == {'select'}:
                mode = selected
                break
            remaining = 30 - elapsed if navigating else min(8 - chooser_elapsed, 30 - elapsed)
            panel.show(render_choice(selected, remaining, navigating=navigating, panelbridge=integrated))
            clock.sleep(0.02)
        owned, panel = panel, None
        owned.close()  # no skip marker may survive a failed close
        choice = {'mode': mode}
        if integrated:
            choice.update(panelbridge=True, boot_id=read_boot_id())
        atomic_write(runtime / 'choice.json', json.dumps(choice) + '\n')
        if mode == 'headless':
            atomic_write(runtime / 'headless', 'headless\n')
        return mode
    except Exception as error:
        print(f'Selector fallback to Desktop: {error}', file=sys.stderr, flush=True)
        clear_choice(runtime)
        return 'desktop'
    finally:
        if panel is not None:
            try:
                panel.close()
            except Exception as error:
                print(f'Selector cleanup failed: {error}', file=sys.stderr, flush=True)
                clear_choice(runtime)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        clear_choice(RUNTIME)
        config = load_config(args.config)
        default = Path('/etc/oled-panel/default').read_text().strip()
        modes = ('wireless', 'desktop', 'headless') if config['panelbridge'] else ('desktop', 'headless')
        if default not in modes:
            raise ValueError('invalid root-owned default')
        config['boot_default'] = default.title()
        choose_boot_mode(config, lambda: PanelHardware(argparse.Namespace(**config)))
        return 0
    except Exception as error:
        print(f'Selector failed, allowing Desktop: {error}', file=sys.stderr, flush=True)
        clear_choice(RUNTIME)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
"""HW-937AB foreground bring-up. No service, power, or boot actions.

Mac preview:
  .venv/bin/python hardware_check.py --preview diagnostic-preview.png

Pi usage after inventory, wiring, and dependency setup:
  python hardware_check.py --bus BUS --address ADDRESS
  python hardware_check.py --bus BUS --address ADDRESS --keys \
      --polarity low --gpiochip CHIP --pins-checked

Supply the observed bus/address/chip. 'low' means each pressed switch
connects to GND; 'high' means each connects to 3.3 V. Never infer polarity.
Pillow is the only Mac dependency. Pi also needs luma.oled, gpiozero and
lgpio with Pi 500 support; install those after checking its OS.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import math
from pathlib import Path
import sys
import time

from PIL import Image, ImageDraw, ImageFont

KEY_NAMES = ("up", "down", "select", "back")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--preview", type=Path, help="save a PNG without accessing hardware")
    parser.add_argument("--bus", type=int, help="observed I2C bus number")
    parser.add_argument("--address", type=lambda s: int(s, 0), choices=(0x3C, 0x3D))
    parser.add_argument("--keys", action="store_true", help="enable the four button inputs")
    parser.add_argument("--polarity", choices=("low", "high"), help="measured pressed level")
    parser.add_argument("--gpiochip", type=int, help="observed RP1 gpiochip number")
    parser.add_argument("--pins", type=int, nargs=4, default=[17, 27, 22, 23],
                        metavar=("K1", "K2", "K3", "K4"), help="BCM GPIO numbers")
    parser.add_argument("--pins-checked", action="store_true",
                        help="confirm these pins have no other electrical/software users")
    parser.add_argument("--rotate", type=int, choices=(0, 2), default=0)
    parser.add_argument("--seconds", type=float, default=60, help="duration, 1 to 300 seconds")
    args = parser.parse_args(argv)
    if not math.isfinite(args.seconds) or not 1 <= args.seconds <= 300:
        parser.error("--seconds must be between 1 and 300")
    if args.bus is not None and args.bus < 0:
        parser.error("--bus cannot be negative")
    if args.gpiochip is not None and args.gpiochip < 0:
        parser.error("--gpiochip cannot be negative")
    if not args.preview and (args.bus is None or args.address is None):
        parser.error("hardware mode requires the observed --bus and --address")
    if args.keys and not args.preview:
        if args.polarity is None or args.gpiochip is None or not args.pins_checked:
            parser.error("--keys requires --polarity, --gpiochip, and --pins-checked")
    if len(set(args.pins)) != 4 or any(pin < 4 or pin > 27 for pin in args.pins):
        parser.error("choose four distinct GPIOs 4..27, excluding I2C and ID pins")
    return args


def render_check(pressed, *, keys_enabled, heartbeat=False):
    frame = Image.new("1", (128, 64))
    draw = ImageDraw.Draw(frame)
    font = ImageFont.load_default(size=10)
    draw.rectangle((0, 0, 127, 63), outline=1)
    draw.line((0, 15, 127, 15), fill=1)
    draw.text((3, 2), "HW-937AB TEST", font=font, fill=1)
    if heartbeat:
        draw.rectangle((121, 4, 124, 7), fill=1)
    if keys_enabled:
        lines = [f"K{i + 1} {name:6} {'DOWN' if name in pressed else 'released'}"
                 for i, name in enumerate(KEY_NAMES)]
    else:
        lines = ["128 x 64 / I2C", "Header ends row 15", "Check all 4 corners", "Buttons not enabled"]
    for row, line in enumerate(lines):
        draw.text((3, 18 + row * 11), line, font=font, fill=1)
    return frame


def read_model():
    try:
        return Path("/proc/device-tree/model").read_text().rstrip("\0\n")
    except OSError:
        return "Unknown (not a verified Pi)"


class PanelHardware:
    """Own display and optional input-only keys, including partial-init cleanup."""
    def __init__(self, args):
        model = read_model()
        if not model.startswith("Raspberry Pi 500 Rev"):
            raise RuntimeError(f"Expected Raspberry Pi 500; found {model!r}")
        driver = Path(f"/sys/bus/i2c/devices/{args.bus}-{args.address:04x}/driver")
        if driver.exists():
            raise RuntimeError("I2C address is owned by a kernel driver; refusing access")
        self._resources = ExitStack()
        self.buttons = {}
        try:
            # Imported only on a verified Pi, never for Mac previews or tests.
            from luma.core.interface.serial import i2c
            from luma.oled.device import ssd1315
            serial = i2c(port=args.bus, address=args.address)
            self._resources.callback(serial.cleanup)
            self.display = ssd1315(serial, width=128, height=64, rotate=args.rotate)
            self._resources.callback(self.display.cleanup)
            if args.keys:
                from gpiozero import Button
                from gpiozero.pins.lgpio import LGPIOFactory
                factory = LGPIOFactory(chip=args.gpiochip)
                self._resources.callback(factory.close)
                for name, pin in zip(KEY_NAMES, args.pins):
                    button = Button(pin, pull_up=args.polarity == "low",
                                    bounce_time=0.03, pin_factory=factory)
                    self._resources.callback(button.close)
                    self.buttons[name] = button
        except BaseException:
            self._resources.close()
            raise

    def show(self, frame):
        self.display.display(frame)

    def read_keys(self):
        return {name for name, button in self.buttons.items() if button.is_pressed}

    def close(self):
        self._resources.close()


def run_check(panel, *, seconds, keys_enabled):
    try:
        start = time.monotonic()
        previous = None
        previous_frame = None
        while time.monotonic() - start < seconds:
            pressed = panel.read_keys()
            if pressed != previous:
                print("Keys: " + (", ".join(sorted(pressed)) or "all released")
                      if keys_enabled else "Display-only test; GPIO keys untouched", flush=True)
                previous = pressed
            frame = render_check(pressed, keys_enabled=keys_enabled,
                                 heartbeat=int(time.monotonic() - start) % 2 == 0)
            data = frame.tobytes()
            if data != previous_frame:
                panel.show(frame)
                previous_frame = data
            time.sleep(0.02)
    finally:
        panel.close()


def main(argv=None):
    args = parse_args(argv)
    if args.preview:
        render_check(set(), keys_enabled=args.keys, heartbeat=True).save(args.preview)
        print(f"Saved {args.preview.resolve()} (software preview; hardware untested)")
        return 0
    try:
        panel = PanelHardware(args)
        print(f"Running for {args.seconds:g}s; Ctrl-C stops and clears the display.")
        run_check(panel, seconds=args.seconds, keys_enabled=args.keys)
    except KeyboardInterrupt:
        print("Stopped.")
    except Exception as error:
        print(f"Hardware check failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

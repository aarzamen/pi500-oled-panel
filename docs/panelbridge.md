# PanelBridge front panel

**Rollout deferred.** The optional source integration is preserved for future
installation. PanelBridge's current startup does not require an OLED; hardware
deployment and support for additional boards are not part of its current
completion gate.

Development integration for the 128×64 OLED and four buttons. The OLED and
PanelBridge run on the same Pi, under the same normal desktop account. Separate
Pi control is not implemented. No SSH keys or remote-control server are added.

The planned rollout uses one OLED per host across Raspberry Pi and Jetson
systems. Shared menus will expose only the actions supported by that host.
Jetson support is not implemented or hardware-verified; its GPIO and startup
integration need a board-specific adapter. The combined Pi 5 setup comes first.

**Implemented and software-tested; not yet installed or hardware-verified.**
The standalone OLED was verified on Pi 500; the wireless monitor was verified on
Pi 5. Those results do not verify either combined configuration. The installer
still checks for the previously tested Pi 500; Pi 5 GPIO support awaits checking
the actual wiring and controller. The published v0.1.0 release is unchanged.

## Startup

| Choice | Behavior for this boot |
| --- | --- |
| Wireless desktop | Start the normal desktop and let PanelBridge connect. |
| Desktop only | Start the normal desktop with monitor streaming stopped. |
| Console only | Skip the display manager; retain the OLED and network access. |

The George splash, eight-second default countdown, thirty-second maximum chooser
time and first-press wake behavior are retained. The saved default remains
Desktop until changed through Boot Default. A one-time choice does not save a
new default. If the OLED or selector fails, the desktop and ordinary PanelBridge
startup remain available.

Wireless desktop requires the desktop session. The previous Headless choice
cannot provide it. Console only still offers Start Desktop from the OLED;
after it starts, use Monitor → Start monitor to begin streaming.

## During use

The Monitor page comes first when integration is enabled. It shows connection
state, configured desktop resolution/content rate, the Pi's LAN address, and a
short status message. K3 opens full details; K4 opens actions.

- Start monitor, or Reconnect after an error.
- Stop monitor while leaving the desktop running.
- Keep display trial or Revert display trial during a pending change.
- Restore last good after an error.
- Start/stop Desktop, saved boot default, reboot and shutdown in the main menu.

Commands follow the controller's available features and current state. Old or
unavailable status disables monitor actions. An accepted command is not physical
proof of an image. The OLED does not send video or manage its own reconnect loop.
Detailed display settings and calibration stay in the larger PanelBridge app.
Resolution is the configured source size, not a measurement of the LCD panel.

Hold confirmation remains required for system actions. Up/down scrolls menus
while keeping the selected row visible. Keep Ethernet connected for recovery;
the LAN address is shown, but this version does not claim an enrolled recovery
web page or measured total input power.

## Installation boundary

Integration is opt-in through `panelbridge: true` in device configuration or the
installer's `--panelbridge` option. Before installation it requires a compatible
PanelBridge capability receipt and matching enrolled desktop UID. A missing or
older PanelBridge package is rejected with an update instruction. Neither app
creates user accounts or changes credentials for this integration.

Do not rerun the installer over an existing installation: both applications
preserve manifests and backups used for restoration. An installed upgrade must
respect those records. No combined deployment has yet been performed.

The boot-choice handoff is local, limited to the current boot UUID and read by
the normal session controller. Invalid, old, foreign-owned or writable-by-other
accounts files do not suppress ordinary startup. The OLED and desktop controllers
remain separate so loss of the OLED cannot own the video session.

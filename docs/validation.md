# Validation and limitations

## Evidence for v0.1.0

These are observations from one Raspberry Pi 500 and HW-937AB module on
2026-10-02. Release preparation uses local tests and packaging checks; it does
not establish compatibility with additional devices.

| Check | Evidence |
| --- | --- |
| Display | 120-second foreground diagnostic; user confirmed upright text, four corners, blinking square, yellow header and blue body |
| Four buttons | 180-second foreground diagnostic; matching presses and releases, active-low inputs on gpiochip 0 |
| Dashboard | 300-second foreground run; user confirmed seven readable pages, live values, details and back navigation |
| Telemetry | RAM and root storage compared with OS tools; adjacent temperature samples and PMIC voltages checked |
| George artwork | Original 128×64 PNG retained byte-for-byte; user confirmed the image and following chooser in an extended preview |
| Desktop startup | Installed selector and desktop started successfully; the complete short visual sequence was missed during the first boot observation |
| Headless startup | After the Plymouth fix, user confirmed the OLED and HDMI text console; boot targets completed, with no pending jobs and SSH/dashboard active |
| Start Desktop from Headless | User confirmed desktop appeared; selector invocation remained unchanged, showing the chooser did not rerun |
| Stop/start Desktop | Installed helper stopped and restarted the manager while SSH and the dashboard continued running |
| Shutdown | User selected Shutdown; Pi and OLED powered off and remote sessions disconnected |
| OLED disconnected | User confirmed a powered-off disconnect followed by a boot to Desktop; that disconnected boot had no remote log capture |
| Isolated systemd cases | Desktop, Headless, initialization failure, failure after marker creation, finish failure, and timeout passed with separate test services on the Pi |
| Automated tests | 73 tests on the development Mac; 23 latest focused action/installer tests on the Pi |

The isolated timeout case completed around 32.4 seconds. The selector service
has a 32-second start timeout and a separate two-second stop timeout. Generated
units and sudoers were validated before installation. These tests cover the
failure paths separately from the physical observations above.

## Device acceptance checklist

Repeat these checks on your own Pi after following [setup](setup.md):

- [ ] Check bus/address, wiring, unused GPIOs, chip number, and button polarity.
- [ ] Confirm display-only and four-button diagnostics, including clean exit.
- [ ] Check all seven dashboard pages, details, long values, and wake-only first
      press after 60 seconds idle.
- [ ] Verify actions in dry-run mode before enabling real actions.
- [ ] Verify the staged units and sudoers, then install.
- [ ] Save work and check Stop Desktop followed by Start Desktop with recovery
      access available.
- [ ] Boot unattended to Desktop and observe the splash, chooser, and dashboard.
- [ ] Boot with an explicit Headless choice; verify the console and required
      background services, then Start Desktop without a second chooser.
- [ ] Shut down, remove power, disconnect the OLED, and boot. Confirm Desktop
      fallback. Shut down and remove power again before reconnecting it.
- [ ] Perform one deliberate OLED shutdown and confirm the Pi powers down.

## Scope and remaining limits

The runtime and installer deliberately accept only the Raspberry Pi 500 model.
The tested setup uses Raspberry Pi OS based on Debian 13 (Trixie), system Python
3.13.5, LightDM, luma.oled 3.15.0, gpiozero 2.0.1, and lgpio 0.2.2. No other board,
display variant, GPIO mapping, display manager, or fresh OS installation has
received the same physical validation. The fresh-install instructions are based
on the installer and observed dependencies; the complete fresh-image procedure
has not been repeated for this release.

Software previews establish layout only. Local unit tests do not exercise real
GPIO, I2C, systemd boot order, or physical power actions. The wheel includes the
George image; deployment scripts and setup files are in the source distribution.

“App Not configured” is expected until a service or endpoint is selected.
A service reported Ready is running; this is not a health check of its internal
application. PMIC readings describe individual rails. Total input watts remain
unavailable without a suitable measurement source. Background work must run
independently of graphical login sessions if it should survive Stop Desktop.

Example addresses in previews and test fixtures use the documentation ranges
`192.0.2.0/24`, `198.51.100.0/24`, and `2001:db8::/32`. Live snapshots and logs can
contain real device details; inspect them before sharing.

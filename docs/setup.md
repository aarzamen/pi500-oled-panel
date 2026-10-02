# Setup and recovery

## 1. Prepare the Pi

Use a Raspberry Pi 500 with Raspberry Pi OS Desktop, a configured nonroot
account with sudo access, and an available local keyboard/monitor or working
SSH connection. The validated OS is based on Debian 13 (Trixie), with system
Python 3.13 and LightDM. The installer requires `graphical.target` and an
existing display manager. It does not convert a Lite/headless OS to Desktop.

Run the blocks in order in **Bash on the Pi as your ordinary account**, not a
root shell. Reconnect after the reboot below. Do not run hardware diagnostics
while another panel process owns the display or GPIO pins.

First inspect the model and existing boot setup:

```bash
tr -d '\0' < /proc/device-tree/model
printf '\n'
/usr/bin/python3 --version
/usr/bin/systemctl get-default
readlink -f /etc/systemd/system/display-manager.service
```

Install the OS dependencies and enable I2C:

```bash
sudo apt-get update
sudo apt-get install -y git python3-venv python3-dev build-essential python3-gpiozero python3-lgpio i2c-tools
PANEL_USER="$(id -un)"
sudo usermod -aG gpio,i2c "$PANEL_USER"
sudo raspi-config nonint do_i2c 0
```

Save your work, then reboot so the hardware interface and group membership take
effect. This interrupts the current session:

```bash
sudo /usr/bin/systemctl reboot
```

## 2. Get the source and Python environment

After reconnecting, use the same ordinary account. The project path must be a
real absolute path without spaces, symlink components, or special characters.
Both source options below create `$HOME/pi500-oled-panel`, the directory used
throughout this guide. Choose **one** option. Each refuses an existing destination;
if that directory already exists, stop and inspect it before continuing.

### Option A: Git checkout

```bash
(
set -eu
PROJECT="$HOME/pi500-oled-panel"
if [ -e "$PROJECT" ] || [ -L "$PROJECT" ]; then
    printf 'Destination already exists: %s\n' "$PROJECT" >&2
    exit 1
fi
git clone https://github.com/aarzamen/pi500-oled-panel.git "$PROJECT"
git -C "$PROJECT" checkout --detach v0.1.0
)
```

### Option B: Downloaded source archive

Download the v0.1.0 source ZIP or `pi500_oled_panel-0.1.0.tar.gz` from the
[release page](https://github.com/aarzamen/pi500-oled-panel/releases/tag/v0.1.0)
to the Pi. The following block asks for its full path, extracts it into a temporary
directory, and copies the source to the canonical project directory. It accepts
an archive with one enclosing directory or source files at its root. Use a source
archive, not the wheel.

```bash
(
set -eu
read -r -p 'Full path to the downloaded source ZIP or .tar.gz: ' SOURCE_ARCHIVE
/usr/bin/python3 - "$SOURCE_ARCHIVE" "$HOME/pi500-oled-panel" <<'PYTHON'
from pathlib import Path
import shutil
import sys
import tarfile
import tempfile
import zipfile

archive = Path(sys.argv[1]).expanduser().resolve(strict=True)
project = Path(sys.argv[2])
if project.exists() or project.is_symlink():
    raise SystemExit(f"Destination already exists: {project}")
with tempfile.TemporaryDirectory(prefix="oled-source-") as temporary:
    staging = Path(temporary)
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as source:
            source.extractall(staging)
    else:
        with tarfile.open(archive) as source:
            source.extractall(staging, filter="data")
    candidates = [staging] + [p for p in staging.iterdir() if p.is_dir()]
    roots = [p for p in candidates if (p / "pyproject.toml").is_file()
             and (p / "config.example.json").is_file()
             and (p / "system/install.sh").is_file()]
    if len(roots) != 1:
        raise SystemExit("Expected one complete project in the source archive")
    shutil.copytree(roots[0], project)
print(f"Source ready at {project}")
PYTHON
)
```

### Create the environment

Continue only after the chosen source block succeeds. Both options now use the
same commands:

```bash
PANEL_USER="$(id -un)"
PROJECT="$HOME/pi500-oled-panel"
cd "$PROJECT"
/usr/bin/python3 -c 'import sys; assert sys.version_info[:2] in ((3, 12), (3, 13)), "Use an OS with system Python 3.12 or 3.13 for this setup"'
/usr/bin/python3 -m venv "$PROJECT/.uv-bootstrap"
"$PROJECT/.uv-bootstrap/bin/python" -m pip install uv
"$PROJECT/.uv-bootstrap/bin/uv" venv --python /usr/bin/python3 --system-site-packages "$PROJECT/.venv"
"$PROJECT/.uv-bootstrap/bin/uv" pip install --python "$PROJECT/.venv/bin/python" -e "$PROJECT[pi]"
cp "$PROJECT/config.example.json" "$PROJECT/config.local.json"
"$PROJECT/.venv/bin/python" -I -c 'import gpiozero, lgpio; from luma.oled.device import ssd1315; import oled_panel.app; print("Hardware imports passed")'
```

The environment deliberately uses the OS Python and `--system-site-packages`:
the GPIO packages installed by apt, especially the compiled `lgpio` extension,
need the matching Python version. A separately downloaded interpreter may not
be able to import them. General software previews can use uv-managed Python
3.12; use the system-matched environment for Pi deployment.

## 3. Check wiring and run foreground diagnostics

Power off and unplug the Pi before wiring the panel using the
[README table](../README.md#wiring). Confirm the module's button polarity and
that the GPIO pins are unused. Reconnect power, log in, and set the paths again:

```bash
PROJECT="$HOME/pi500-oled-panel"
cd "$PROJECT"
id
ls -l /dev/i2c-1 /dev/gpiochip*
/usr/sbin/i2cdetect -l
sudo /usr/sbin/i2cdetect -y 1 0x3c 0x3d
```

The limited probe is for the two supported OLED addresses on the expected bus.
The tested module responded at `0x3c`. Stop if no address responds, an address
shows `UU` (a kernel driver owns it), or the wiring differs. Adjust the diagnostic
arguments and `config.local.json` only to match your observed hardware. The
following commands assume the tested bus, address, chip, and active-low buttons:

```bash
"$PROJECT/.venv/bin/python" -m hardware_check --bus 1 --address 0x3c --seconds 120
"$PROJECT/.venv/bin/python" -m hardware_check --bus 1 --address 0x3c --keys --polarity low --gpiochip 0 --pins-checked --seconds 180
"$PROJECT/.venv/bin/python" -m oled_panel.app --foreground --dry-run-actions --config "$PROJECT/config.local.json" --seconds 180
```

Check four visible corners, upright text, the blinking square, and every matching
button press/release. Then check all seven dashboard pages and their details.
Each command runs to completion and releases the hardware; Ctrl-C also exits.
The last command only logs requested actions. It does not stop Desktop, change
the saved default, reboot, or shut down.

Choose any optional workload monitor in `config.local.json` now. Run the dry-run
dashboard again after configuration edits.

## 4. Stage and inspect the installation

Create a unique staging parent; its `files` child must not already exist.
Rendering checks the real Pi, account, Python environment, configuration, boot
target, and resolved display manager without installing anything:

```bash
PANEL_USER="$(id -un)"
PROJECT="$HOME/pi500-oled-panel"
STAGE_PARENT="$(mktemp -d "$HOME/oled-panel-stage.XXXXXX")"
STAGE="$STAGE_PARENT/files"
MANAGER="$(basename "$(readlink -f /etc/systemd/system/display-manager.service)")"
/bin/sh "$PROJECT/system/install.sh" --user "$PANEL_USER" --project "$PROJECT" --config "$PROJECT/config.local.json" --render-only "$STAGE"
sudo /usr/bin/env SYSTEMD_UNIT_PATH="$STAGE/etc/systemd/system:/etc/systemd/system:/run/systemd/system:/usr/lib/systemd/system" /usr/bin/systemd-analyze verify --man=no "$STAGE/etc/systemd/system/oled-panel-selector.service" "$STAGE/etc/systemd/system/oled-panel.service" "$MANAGER"
sudo /usr/sbin/visudo -cf "$STAGE/etc/sudoers.d/oled-panel"
cat "$STAGE/etc/systemd/system/oled-panel-selector.service" "$STAGE/etc/systemd/system/oled-panel.service"
cat "$STAGE/etc/systemd/system/$MANAGER.d/60-oled-panel.conf"
cat "$STAGE/etc/sudoers.d/oled-panel"
cat "$STAGE/etc/oled-panel/device.json"
```

Inspect the account, paths, manager, and device configuration. Both validation
commands must succeed before proceeding.

## 5. Install, then check the running panel

```bash
sudo /bin/sh "$PROJECT/system/install.sh" --user "$PANEL_USER" --project "$PROJECT" --config "$PROJECT/config.local.json"
```

The installer validates units and sudoers again, installs root-owned system
files, and enables the dashboard for the next boot. It starts no services and
performs no power or Desktop action. The dashboard and GPIO access use your
nonroot account; a separate stdlib-only root helper allows exactly six command
forms: start Desktop, stop Desktop, reboot, shutdown, and the two saved defaults.

Before trying live actions, save graphical work. Start the selector alone and
wait for it to finish. With the initial Desktop default, leave it unattended:

```bash
sudo /usr/bin/systemctl start oled-panel-selector.service
"$PROJECT/.venv/bin/python" -I -m oled_panel.app --foreground --real-actions --config /etc/oled-panel/device.json --seconds 180
```

The foreground dashboard now has **real actions enabled**. Check one action at
a time. For example, confirm Stop Desktop, observe the console and continuing
background services, then confirm Start Desktop. Reboot and shutdown interrupt
the machine. K4 cancels a pending confirmation. The selector is run first so a
Start Desktop request cannot create a second chooser while the dashboard owns
the hardware.

After the foreground process exits, start the daemon:

```bash
sudo /usr/bin/systemctl start oled-panel.service
sudo /usr/bin/systemctl status oled-panel-selector.service oled-panel.service --no-pager
sudo /usr/bin/journalctl -u oled-panel-selector.service -u oled-panel.service -n 80 --no-pager
```

Logs may contain your hostname, addresses, or application endpoint. Keep them
private or review and redact them before sharing.

## 6. Supervised boot checks

Keep console or SSH recovery available and save work. Reboot deliberately:

```bash
sudo /usr/bin/systemctl reboot
```

First let the chooser use Desktop. Then repeat and choose Headless explicitly.
Check the George image, chooser, dashboard, HDMI console, and your own background
services. From Headless, select Start Desktop and verify that the desktop starts
without repeating the chooser. Follow the rest of the
[device acceptance checklist](validation.md#device-acceptance-checklist),
including the disconnected-display fallback and deliberate shutdown.

## Recovery

From your Pi console or SSH shell, request Desktop through the installed helper:

```bash
sudo -n /usr/local/libexec/oled-panel-action start-desktop
```

If the helper itself is damaged, resolve the existing manager and start it
explicitly after removing the temporary skip marker:

```bash
MANAGER="$(basename "$(readlink -f /etc/systemd/system/display-manager.service)")"
sudo /usr/bin/rm -f /run/oled-panel/headless
sudo /usr/bin/systemctl start "$MANAGER"
```

To inspect failures:

```bash
sudo /usr/bin/journalctl -b -u oled-panel-selector.service -u oled-panel.service --no-pager
/usr/bin/systemctl list-jobs
/usr/bin/systemctl get-default
```

The selector failure path allows Desktop even when Headless was saved. A missing
OLED is handled within the bounded selector timeout. The dashboard may retry
while hardware is unavailable; stop its service before troubleshooting hardware.

## Uninstall and configuration changes

Uninstall preserves the source, environment, backup, existing boot target, and
display-manager alias. Stop both panel services first, then remove integration
and restore Desktop:

```bash
PROJECT="$HOME/pi500-oled-panel"
MANAGER="$(basename "$(readlink -f /etc/systemd/system/display-manager.service)")"
sudo /usr/bin/systemctl stop oled-panel.service oled-panel-selector.service
sudo /bin/sh "$PROJECT/system/uninstall.sh"
sudo /usr/bin/systemctl start "$MANAGER"
/usr/bin/systemctl get-default
```

The installer refuses existing owned paths and existing backup directories.
Its root-only record is `/var/lib/oled-panel/install-backup/manifest.json`.
Uninstall checks ownership, permissions, and digests before removing files;
unexpected edits are preserved and cause it to stop for inspection. A saved
default changed through the OLED menu is allowed. An interrupted installation
with an incomplete manifest needs manual inspection.

For configuration changes beyond the Boot Default menu, use a deliberate
uninstall, edit, stage, and reinstall cycle. Do not edit the installed copy and
expect an automatic upgrade. After a successful uninstall, archive the retained
backup under a unique name before reinstalling:

```bash
BACKUP_ARCHIVE="/var/lib/oled-panel/install-backup-$(date -u +%Y%m%dT%H%M%SZ)"
sudo test ! -e "$BACKUP_ARCHIVE" && sudo mv /var/lib/oled-panel/install-backup "$BACKUP_ARCHIVE"
```

Keep that backup for recovery. Edit `config.local.json`, repeat the foreground
checks, and stage into a new directory before installing again. Installation
initializes the saved default to Desktop. Uninstall does not undo the separately
performed I2C setup or group membership changes.

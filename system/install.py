#!/usr/bin/python3 -I
"""Stage, install or remove the OLED panel's explicitly owned system files."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import stat
import subprocess
import tempfile

BACKUP = Path('var/lib/oled-panel/install-backup')
HELPER = '/usr/local/libexec/oled-panel-action'
PANELBRIDGE_ENROLLMENT = Path('/etc/panelbridge/enrollment.json')
PANELBRIDGE_CAPABILITY = Path('/usr/share/panelbridge/oled-integration.json')


def render(user, project, config, manager):
    integrated = config.get('panelbridge', False)
    if type(integrated) is not bool:
        raise ValueError('panelbridge must be boolean')
    if not re.fullmatch(r'[a-z_][a-z0-9_-]*', user):
        raise ValueError('user must be a simple local account name')
    if not re.fullmatch(r'/[A-Za-z0-9_./-]+', project) or '..' in Path(project).parts:
        raise ValueError('project must be an absolute path without spaces or special characters')
    if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.@-]*\.service', manager):
        raise ValueError('display manager must be a .service name')
    artifacts = {}
    def add(path, text, mode=0o644):
        artifacts[path.lstrip('/')] = {'data': text.encode(), 'mode': mode}
    common = f'User={user}\nSupplementaryGroups=gpio i2c\nWorkingDirectory={project}\nUMask=0022\n'
    add('/etc/systemd/system/oled-panel-selector.service', f'''[Unit]
Description=Bounded OLED boot selector
Before={manager} oled-panel.service

[Service]
Type=oneshot
{common}RuntimeDirectory=oled-panel
RuntimeDirectoryMode=0755
RuntimeDirectoryPreserve=yes
ExecStartPre=+/usr/bin/python3 -I {HELPER} selector-reset
ExecStart={project}/.venv/bin/python -I -m oled_panel.boot --config /etc/oled-panel/device.json
ExecStartPost=+/usr/bin/python3 -I {HELPER} selector-finish
ExecStopPost=+/usr/bin/python3 -I {HELPER} selector-cleanup
TimeoutStartSec=32s
TimeoutStopSec=2s
KillMode=control-group
RemainAfterExit=yes
NoNewPrivileges=yes
''')
    add('/etc/systemd/system/oled-panel.service', f'''[Unit]
Description=OLED status panel
Wants=oled-panel-selector.service
After=oled-panel-selector.service

[Service]
Type=simple
{common}ExecStart={project}/.venv/bin/python -I -m oled_panel.app --daemon --config /etc/oled-panel/device.json
TimeoutStopSec=3s
KillMode=control-group
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
''')
    add(f'/etc/systemd/system/{manager}.d/60-oled-panel.conf', '''[Unit]
Wants=oled-panel-selector.service
After=oled-panel-selector.service
ConditionPathExists=!/run/oled-panel/headless
''')
    allowed = ['start-desktop', 'stop-desktop', 'reboot', 'shutdown',
               'set-default desktop', 'set-default headless']
    if integrated:
        allowed.append('set-default wireless')
    add('/etc/sudoers.d/oled-panel', f'{user} ALL=(root) NOPASSWD: ' +
        ', '.join(f'{HELPER} {action}' for action in allowed) + '\n', 0o440)
    add('/etc/oled-panel/actions.json', json.dumps({'display_manager': manager, 'panelbridge': integrated}, indent=2) + '\n')
    add('/etc/oled-panel/default', 'desktop\n')
    device = dict(config); device['display_manager'] = manager; device['boot_default'] = 'Desktop'
    device['panelbridge'] = integrated
    add('/etc/oled-panel/device.json', json.dumps(device, indent=2) + '\n')
    artifacts[HELPER.lstrip('/')] = {'data': Path(__file__).with_name('oled-panel-action').read_bytes(), 'mode': 0o755}
    artifacts['etc/systemd/system/multi-user.target.wants/oled-panel.service'] = {
        'link': '/etc/systemd/system/oled-panel.service'}
    return artifacts


def run(command, **kwargs):
    return subprocess.run(command, check=True, capture_output=True, text=True,
                          timeout=60, **kwargs).stdout.strip()


def safe_parents(root, path, *, owner=None):
    """Reject redirected or writable system directories before privileged writes."""
    for parent in reversed(path.parents):
        if parent == root or root not in parent.parents:
            continue
        if parent.is_symlink():
            raise PermissionError(f'symlink system directory: {parent}')
        if parent.exists():
            info = parent.stat()
            if not parent.is_dir() or info.st_mode & 0o022 or (owner and info.st_uid != owner[0]):
                raise PermissionError(f'unsafe system directory: {parent}')


def write_file(path, item, owner=None):
    if 'link' in item:
        path.symlink_to(item['link'])
    else:
        fd, temp = tempfile.mkstemp(prefix='.oled-install-', dir=path.parent)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(item['data']); stream.flush(); os.fsync(stream.fileno())
            os.chmod(temp, item['mode'])
            if owner: os.chown(temp, *owner)
            os.replace(temp, path)
        finally:
            Path(temp).unlink(missing_ok=True)
    if owner and path.is_symlink(): os.lchown(path, *owner)


def stage(artifacts, destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    for name, item in artifacts.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        write_file(path, item)


def signature(path):
    if path.is_symlink(): return {'link': os.readlink(path)}
    if not path.exists(): return None
    info = path.stat()
    if not path.is_file(): raise FileExistsError(f'expected file: {path}')
    return {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'mode': stat.S_IMODE(info.st_mode), 'uid': info.st_uid, 'gid': info.st_gid}


def save_manifest(backup, manifest, owner=None):
    write_file(backup / 'manifest.json', {'data': (json.dumps(manifest, indent=2) + '\n').encode(), 'mode': 0o600}, owner)


def restore(root, manifest):
    for item in reversed(manifest['files']):
        path = root / item['path']
        # First installs refuse all pre-existing files. Preserve the explicit
        # absent state for each touched leaf in the manifest.
        if item['previous'] is not None:
            raise RuntimeError('unsupported pre-existing file in manifest')
        path.unlink(missing_ok=True)
    for directory in reversed(manifest['created_dirs']):
        try: (root / directory).rmdir()
        except (FileNotFoundError, OSError): pass  # keep unrelated additions


def install(root, artifacts, original, runner=run, *, owner=(0, 0)):
    root = Path(root)
    backup = root / BACKUP
    safe_parents(root, backup, owner=owner)
    if backup.exists() or backup.is_symlink():
        raise FileExistsError(f'backup already exists: {backup}; retain/archive it before reinstalling')
    for name in artifacts:
        path = root / name
        safe_parents(root, path, owner=owner)
        if path.exists() or path.is_symlink():
            raise FileExistsError(f'refusing unmanaged path: {path}')
    panel_dir = root / 'etc/oled-panel'
    if panel_dir.exists():
        raise FileExistsError(f'refusing unmanaged directory: {panel_dir}')
    backup.mkdir(parents=True, mode=0o700)
    os.chmod(backup, 0o700); os.chown(backup, *owner)
    manifest = {'version': 1, 'state': 'preparing', 'original': original,
                'created_dirs': [], 'files': [{'path': name, 'previous': None} for name in artifacts]}
    save_manifest(backup, manifest, owner)
    try:
        for name, item in artifacts.items():
            path = root / name
            missing = [parent for parent in path.parents if root in parent.parents and not parent.exists()]
            for directory in reversed(missing):
                manifest['created_dirs'].append(str(directory.relative_to(root)))
                save_manifest(backup, manifest, owner)
                directory.mkdir(mode=0o755)
                os.chown(directory, *owner)
            write_file(path, item, owner)
        for item in manifest['files']: item['installed'] = signature(root / item['path'])
        manifest['state'] = 'installed'
        save_manifest(backup, manifest, owner)
        runner(['/usr/bin/systemctl', 'daemon-reload'])
    except BaseException:
        restore(root, manifest)
        manifest['state'] = 'rolled-back'
        save_manifest(backup, manifest, owner)
        try: runner(['/usr/bin/systemctl', 'daemon-reload'])
        except Exception: pass
        raise


def uninstall(root, runner=run):
    root = Path(root); backup = root / BACKUP
    manifest = json.loads((backup / 'manifest.json').read_text())
    if manifest['state'] in ('uninstalled', 'rolled-back'):
        return
    if manifest['state'] != 'installed' or any('installed' not in item for item in manifest['files']):
        raise RuntimeError('incomplete installation; inspect root backup and existing paths before manual recovery')
    for item in manifest['files']:
        path = root / item['path']
        safe_parents(root, path)
        actual = signature(path)
        expected = item.get('installed')
        if item['path'] == 'etc/oled-panel/default' and actual:
            # Changing the saved default is an owned runtime operation.
            actual = dict(actual); actual['sha256'] = (expected or actual)['sha256']
        if actual is not None and expected is not None and actual != expected:
            raise RuntimeError(f'installed file changed; inspect before removal: {path}')
    runtime = root / 'run/oled-panel'
    if runtime.is_symlink(): raise PermissionError('runtime directory is a symlink')
    for name in ('headless', 'choice.json'):
        (runtime / name).unlink(missing_ok=True)
    restore(root, manifest)
    manifest['state'] = 'uninstalled'
    save_manifest(backup, manifest)
    runner(['/usr/bin/systemctl', 'daemon-reload'])


def read_panelbridge_record(path, label):
    """Read one fixed installed record through pinned, root-owned directories."""
    if path not in (PANELBRIDGE_ENROLLMENT, PANELBRIDGE_CAPABILITY):
        raise ValueError('unsupported PanelBridge record')
    directory = None
    try:
        for part in path.parent.parts:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            if directory is not None:
                os.close(directory)
            directory = child
            info = os.fstat(directory)
            if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
                raise PermissionError('unsafe record parent')
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                     dir_fd=directory)
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022
                    or info.st_nlink != 1):
                raise PermissionError('unsafe record file')
            raw = stream.read(65537)
    except FileNotFoundError:
        raise RuntimeError(f'PanelBridge {label} is missing; integration requires an installed, enrolled desktop account') from None
    except OSError:
        raise RuntimeError(f'PanelBridge {label} is unsafe or unreadable; preserve it and inspect ownership and permissions') from None
    finally:
        if directory is not None:
            os.close(directory)
    try:
        if len(raw) > 65536:
            raise ValueError
        def unique_object(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError('duplicate record key')
                result[key] = value
            return result
        return json.loads(raw, object_pairs_hook=unique_object)
    except (ValueError, TypeError, RecursionError):
        raise RuntimeError(f'PanelBridge {label} is invalid; expected a bounded JSON record') from None


def validate_panelbridge_integration(uid):
    enrollment = read_panelbridge_record(PANELBRIDGE_ENROLLMENT, 'enrollment')
    try:
        if not isinstance(enrollment, dict) or set(enrollment) - {'api_version', 'normal_uid', 'rescue_uid'}:
            raise ValueError
        normal, rescue = enrollment['normal_uid'], enrollment.get('rescue_uid')
        if (type(enrollment.get('api_version')) is not int or enrollment['api_version'] != 1
                or type(normal) is not int or not 1000 <= normal < 2**31
                or (rescue is not None and (type(rescue) is not int or not 0 < rescue < 2**31 or rescue == normal))):
            raise ValueError
    except (ValueError, KeyError, TypeError):
        raise RuntimeError('PanelBridge enrollment is invalid; expected a supported desktop-account binding') from None
    if normal != uid:
        raise ValueError('OLED --user must match the PanelBridge enrolled desktop account')
    try:
        capability = read_panelbridge_record(PANELBRIDGE_CAPABILITY, 'OLED capability receipt')
        if (not isinstance(capability, dict) or set(capability) != {'api_version', 'startup_choice', 'session_bus'}
                or type(capability.get('api_version')) is not int or capability['api_version'] != 1
                or type(capability.get('startup_choice')) is not int or capability['startup_choice'] != 1
                or capability.get('session_bus') != 'org.panelbridge.Session1'):
            raise ValueError
    except (RuntimeError, ValueError):
        raise RuntimeError('Update PanelBridge before enabling OLED integration: its OLED capability receipt is missing, unsafe or unsupported') from None


def preflight(args):
    model = Path('/proc/device-tree/model').read_text().rstrip('\0\n')
    if not model.startswith('Raspberry Pi 500 Rev'):
        raise RuntimeError(f'expected verified Pi 500, found {model!r}')
    account = pwd.getpwnam(args.user)
    if account.pw_uid == 0: raise ValueError('dashboard must be nonroot')
    project = Path(args.project)
    if project.resolve() != project or not project.is_dir():
        raise ValueError('project must be a real absolute directory, without symlink components')
    python = project / '.venv/bin/python'
    if not python.is_file() or not os.access(python, os.X_OK): raise ValueError('missing executable project venv')
    config = Path(args.config).resolve(strict=True)
    # Execute user-maintained Python only as the dashboard account.
    check = [str(python), '-I', '-c',
             'import sys; from oled_panel.config import load_config; import oled_panel.boot; '
             'import oled_panel.app; import hardware_check; import luma.oled.device; '
             'import gpiozero; assert sys.version_info >= (3, 12); '
             'assert load_config(sys.argv[1])["keys"] is True', str(config)]
    if os.geteuid() == 0: check = ['/usr/sbin/runuser', '-u', args.user, '--'] + check
    elif os.getuid() != account.pw_uid: raise PermissionError('render as the dashboard user or root')
    run(check)
    supplied = json.loads(config.read_text())
    if not isinstance(supplied, dict) or type(supplied.get('panelbridge', False)) is not bool:
        raise ValueError('panelbridge must be boolean in the device configuration')
    if supplied.get('panelbridge', False) or getattr(args, 'panelbridge', False):
        validate_panelbridge_integration(account.pw_uid)
    resolved = Path('/etc/systemd/system/display-manager.service').resolve(strict=True)
    manager = resolved.name
    if not resolved.is_file(): raise ValueError('missing resolved display manager')
    target = run(['/usr/bin/systemctl', 'get-default'])
    if target != 'graphical.target': raise ValueError('expected existing graphical.target; refusing to change it')
    return supplied, manager, {'default_target': target, 'display_manager': manager,
           'display_manager_path': str(resolved), 'display_manager_alias': os.readlink('/etc/systemd/system/display-manager.service')}


def verify(staging, manager):
    directory = staging / 'etc/systemd/system'
    environment = dict(os.environ)
    environment['SYSTEMD_UNIT_PATH'] = str(directory) + ':/etc/systemd/system:/run/systemd/system:/usr/lib/systemd/system'
    run(['/usr/bin/systemd-analyze', 'verify', '--man=no',
         str(directory / 'oled-panel-selector.service'), str(directory / 'oled-panel.service'), manager], env=environment)
    run(['/usr/sbin/visudo', '-cf', str(staging / 'etc/sudoers.d/oled-panel')])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--uninstall', action='store_true')
    parser.add_argument('--render-only', type=Path, help='new staging directory; no system writes or activation')
    parser.add_argument('--user')
    parser.add_argument('--project')
    parser.add_argument('--config')
    parser.add_argument('--panelbridge', action='store_true',
                        help='enable same-host PanelBridge boot choices; saved default remains Desktop')
    args = parser.parse_args(argv)
    if args.uninstall:
        if os.geteuid() != 0: parser.error('uninstall requires sudo')
        # Stop only our display/selector services, never the display manager.
        # The separate recovery command makes this interruption explicit.
        for unit in ('oled-panel.service', 'oled-panel-selector.service'):
            active = subprocess.run(['/usr/bin/systemctl', 'is-active', '--quiet', unit]).returncode == 0
            if active: raise RuntimeError('stop oled-panel.service and oled-panel-selector.service before uninstalling')
        uninstall(Path('/'))
        print('OLED startup integration removed; source, venv, and backup retained.')
        return
    if not all((args.user, args.project, args.config)):
        parser.error('--user, --project and --config are required')
    if not args.render_only and os.geteuid() != 0: parser.error('installation requires sudo')
    config, manager, original = preflight(args)
    if args.panelbridge:
        config = {**config, 'panelbridge': True}
    artifacts = render(args.user, args.project, config, manager)
    if args.render_only:
        stage(artifacts, args.render_only)
        print(f'Staged exact install files at {args.render_only}; no system files changed.')
        return
    with tempfile.TemporaryDirectory(prefix='oled-install-') as temp:
        staging = Path(temp) / 'stage'
        stage(artifacts, staging)
        verify(staging, manager)
        install(Path('/'), artifacts, original)
    print('Installed and enabled for next boot. No services started; no desktop or power action executed.')


if __name__ == '__main__':
    try: main()
    except Exception as error:
        raise SystemExit(f'Install/recovery failed: {error}')

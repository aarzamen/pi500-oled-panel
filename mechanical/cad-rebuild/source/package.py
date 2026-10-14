"""Build a public case-only ZIP and SHA-256 manifests from a reviewed kit."""
import argparse
import hashlib
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED


ZIP_NAME = 'OLED-case-CAD-v3-public.zip'
ROOT_FILES = {'README.md', 'LICENSE', 'assembly-preview.png', 'case-preview.png',
              'stand-preview.png', 'OLED-case-CAD-v3.3mf',
              '.cad-v3-output.json'}
FOLDERS = {'STL', 'STEP', 'source', 'evidence'}
SKIP = {'.venv', '__pycache__', '.git'}
PARTS = {'front', 'button-cap', 'back-dual-knockouts', 'back-upper-open',
         'back-lower-open', 'stand'}


def package(kit):
    kit = Path(kit)
    files = []
    for path in sorted(kit.rglob('*')):
        if not path.is_file():
            continue
        relative = path.relative_to(kit)
        if any(part in SKIP for part in relative.parts):
            continue
        if relative.parts[0] not in FOLDERS and relative.as_posix() not in ROOT_FILES:
            continue
        if relative.parts[0] == 'STL' and relative.as_posix() not in {f'STL/{p}.stl' for p in PARTS}:
            continue
        if relative.parts[0] == 'STEP' and relative.as_posix() not in \
                ({f'STEP/{p}.step' for p in PARTS} | {'STEP/enclosure-only.step'}):
            continue
        files.append((relative.as_posix(), path.read_bytes()))
    manifest = ''.join(f'{hashlib.sha256(data).hexdigest()}  {name}\n' for name, data in files)
    (kit / 'SHA256SUMS.txt').write_text(manifest)
    files.append(('SHA256SUMS.txt', manifest.encode()))
    archive = kit / ZIP_NAME
    with ZipFile(archive, 'w', ZIP_DEFLATED) as output:
        for name, data in files:
            entry = ZipInfo('OLED-case-CAD-v3-public/' + name, date_time=(2026, 10, 14, 0, 0, 0))
            entry.compress_type = ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            output.writestr(entry, data)
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    (kit / (ZIP_NAME + '.sha256')).write_text(f'{checksum}  {ZIP_NAME}\n')
    return archive, checksum, len(files)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kit', type=Path, required=True, help='Reviewed public kit directory')
    args = parser.parse_args()
    archive, checksum, count = package(args.kit)
    print(f'{archive.name}: {count} files; SHA-256 {checksum}')

#!/usr/bin/env python3
"""Fetch verified SCMapDB packs into Newport's external game-data directory."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import urllib.request
import zipfile


def install(name, spec, data):
    data.mkdir(parents=True, exist_ok=True)
    archive = data / spec['archive']
    if not archive.exists():
        partial = archive.with_suffix(archive.suffix + '.part')
        try:
            with urllib.request.urlopen(spec['url'], timeout=60) as src, partial.open('wb') as dst:
                shutil.copyfileobj(src, dst)
            partial.rename(archive)
        finally:
            partial.unlink(missing_ok=True)
    with archive.open('rb') as source:
        digest = hashlib.file_digest(source, 'sha256').hexdigest()
    if digest != spec['sha256']:
        raise ValueError(f'{archive}: SHA256 mismatch; nothing installed')
    custom = (data / 'custom').resolve()
    prefix = spec.get('strip_prefix', '')
    entries = []
    with zipfile.ZipFile(archive) as pack:
        for member in pack.infolist():
            raw = member.filename.replace('\\', '/')
            path = Path(raw)
            if path.is_absolute() or '..' in path.parts or (member.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError(f'Unsafe archive member: {raw}')
            if prefix and not raw.startswith(prefix):
                raise ValueError(f'Unexpected archive root: {raw}')
            relative = Path(raw[len(prefix):])
            target = (custom / relative).resolve()
            if not target.is_relative_to(custom):
                raise ValueError(f'Archive member escapes asset directory: {raw}')
            entries.append((member, target))
        if not any(target == custom / 'maps' / f'{name}.bsp' for _, target in entries):
            raise ValueError(f'Archive does not contain maps/{name}.bsp')
        for member, target in entries:
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with pack.open(member) as src, target.open('wb') as dst:
                    shutil.copyfileobj(src, dst)
    print(f'{name}: SHA256 verified; installed in {custom}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('maps', nargs='+', help='BSP names listed in maps.json')
    parser.add_argument('--data-dir', type=Path, default=Path('/mnt/terrabud/games/svencoop'))
    args = parser.parse_args()
    manifest = json.loads(Path(__file__).with_name('maps.json').read_text())['maps']
    for name in args.maps:
        if name not in manifest:
            parser.error(f'Unknown map: {name}')
    try:
        for name in args.maps:
            install(name, manifest[name], args.data_dir)
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()

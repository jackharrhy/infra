#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = Path('/mnt/terrabud/docker-data/newport/cheesetown/provisioned-mods')


def provision(mods, output, custom_dir):
    output = Path(output).resolve()
    if output.is_relative_to(ROOT):
        raise ValueError('JAR output must be outside the infra checkout')
    output.mkdir(parents=True, exist_ok=True)
    for mod in mods:
        name = mod['filename']
        if Path(name).name != name or not name.endswith('.jar'):
            raise ValueError(f'Invalid artifact filename: {name}')
        target = output / name
        if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == mod['sha256']:
            print(f'verified {name}')
            continue
        if 'source_url' in mod:
            if not mod['source_url'].startswith('https://'):
                raise ValueError(f'HTTPS required for {name}')
            with urllib.request.urlopen(mod['source_url'], timeout=120) as response:
                data = response.read()
        else:
            if custom_dir is None:
                raise ValueError(f'{name} requires --custom-dir with the pinned local build')
            data = (Path(custom_dir) / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != mod['sha256']:
            raise ValueError(f'SHA-256 mismatch: {name}')
        fd, tmp = tempfile.mkstemp(prefix='.artifact-', dir=output)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(data)
                os.fchmod(stream.fileno(), 0o644)
            os.replace(tmp, target)
        finally:
            Path(tmp).unlink(missing_ok=True)
        print(f'provisioned {name}')
    expected = {mod['filename'] for mod in mods}
    extras = {p.name for p in output.glob('*.jar')} - expected
    if extras:
        raise ValueError(f'Unexpected JARs in output; remove them explicitly: {sorted(extras)}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Provision pinned Cheesetown JARs outside Git.')
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--custom-dir', type=Path)
    args = parser.parse_args()
    manifest = ROOT / 'hosts/newport/cheesetown/fabric-mods/runtime-manifest.json'
    provision(json.loads(manifest.read_text())['mods'], args.output, args.custom_dir)

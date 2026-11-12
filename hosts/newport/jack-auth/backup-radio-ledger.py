#!/usr/bin/env python3
"""Snapshot the Auth UI's Radio ledger and, once present, access-management DB."""
import argparse
from contextlib import closing
import datetime
import json
import os
from pathlib import Path
import sqlite3
import uuid

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--source', type=Path, default=Path('/mnt/terrabud/docker-data/newport/jack-auth/ui/radio-enrollment.sqlite'))
p.add_argument('--access-source', type=Path, help='Defaults to access.sqlite beside the Radio ledger')
p.add_argument('--directory', type=Path, default=Path('/mnt/terrabud/backups/jack-auth/radio-ledger'))
a = p.parse_args()
access = a.access_source or a.source.parent / 'access.sqlite'
if not a.source.is_file() or a.source.is_symlink():
    p.error('Ledger is missing or is a symlink; refusing an empty recovery point')
if access.is_symlink() or (access.exists() and not access.is_file()):
    p.error('Access database must be a regular file, not a symlink')
os.umask(0o077)
a.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
if a.directory.is_symlink() or a.directory.stat().st_mode & 0o777 != 0o700:
    p.error('Backup directory must be private mode0700, not a symlink')
access_required = a.directory / '.access-required'
if access_required.exists() and not access.is_file():
    p.error('Access database is required after adoption; refusing a Radio-only recovery point')
name = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex


def snapshot(source_path, target):
    partial = target.with_name('.' + target.name)
    with closing(sqlite3.connect(source_path.resolve().as_uri() + '?mode=ro', uri=True)) as source:
        with closing(sqlite3.connect(partial)) as destination:
            source.backup(destination)
            if destination.execute('PRAGMA integrity_check').fetchone() != ('ok',):
                raise RuntimeError('SQLite snapshot integrity failed')
    os.chmod(partial, 0o600)
    with partial.open('rb') as f:
        os.fsync(f.fileno())
    os.link(partial, target)
    partial.unlink()
    with closing(sqlite3.connect(target.resolve().as_uri() + '?mode=ro', uri=True)) as check:
        if check.execute('PRAGMA integrity_check').fetchone() != ('ok',):
            raise RuntimeError('Published SQLite snapshot integrity failed')


target = a.directory / (name + '.sqlite')
snapshot(a.source, target)
with closing(sqlite3.connect(target.resolve().as_uri() + '?mode=ro', uri=True)) as check:
    count = check.execute('SELECT COUNT(*) FROM radio_memberships').fetchone()[0]
access_target = None
if access.is_file():
    access_target = a.directory / (name + '.access.sqlite')
    snapshot(access, access_target)
    access_required.touch(mode=0o600, exist_ok=True)
receipt = {'snapshot': str(target), 'rows': count, 'integrity': 'ok',
           'accessSnapshot': str(access_target) if access_target else None,
           'accessState': 'present' if access_target else 'absent-before-adoption',
           'consistency': 'SQLite-consistent per database; quiesce UI for a shared cross-database recovery point'}
manifest = a.directory / (name + '.json')
with manifest.open('x') as f:
    json.dump(receipt, f)
    f.flush()
    os.fsync(f.fileno())
print(json.dumps({**receipt, 'manifest': str(manifest)}))

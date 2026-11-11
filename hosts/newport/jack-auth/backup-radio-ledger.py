#!/usr/bin/env python3
"""Preserve Radio enrollment security state using a consistent SQLite snapshot."""
import argparse
import datetime
import json
import os
from pathlib import Path
import sqlite3
import uuid

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--source', type=Path, default=Path('/mnt/terrabud/docker-data/newport/jack-auth/ui/radio-enrollment.sqlite'))
p.add_argument('--directory', type=Path, default=Path('/mnt/terrabud/backups/jack-auth/radio-ledger'))
a = p.parse_args()
if not a.source.is_file() or a.source.is_symlink():
    p.error('Ledger is missing or is a symlink; refusing an empty recovery point')
os.umask(0o077)
a.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
if a.directory.is_symlink() or a.directory.stat().st_mode & 0o777 != 0o700:
    p.error('Backup directory must be private mode0700, not a symlink')
name = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex
partial = a.directory / ('.' + name + '.sqlite')
target = a.directory / (name + '.sqlite')
with sqlite3.connect(a.source.resolve().as_uri() + '?mode=ro', uri=True) as source:
    with sqlite3.connect(partial) as destination:
        source.backup(destination)
        if destination.execute('PRAGMA integrity_check').fetchone() != ('ok',):
            raise RuntimeError('Ledger snapshot integrity failed')
        count = destination.execute('SELECT COUNT(*) FROM radio_memberships').fetchone()[0]
os.chmod(partial, 0o600)
with partial.open('rb') as f:
    os.fsync(f.fileno())
os.link(partial, target)
partial.unlink()
with sqlite3.connect(target.resolve().as_uri() + '?mode=ro', uri=True) as check:
    assert check.execute('PRAGMA integrity_check').fetchone() == ('ok',)
print(json.dumps({'snapshot': str(target), 'rows': count, 'integrity': 'ok'}))

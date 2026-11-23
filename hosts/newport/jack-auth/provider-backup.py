#!/usr/bin/env python3
"""Newport logical provider backup; all persistent dump bytes are ciphertext."""
import argparse
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import uuid

MOUNT = '/mnt/stash/newport'
SOURCE = '192.168.2.31:/volume1/newport'
STORE = 'jack-auth-postgres-v1'
RECIPIENT = 'age1pxvmxa7pqmaxsxhhe7d9rfs2glaqtzxkpkmhz5lzkcalrgtpzp2s4ap0uu'
IDENTITY = Path.home() / '.config/sops/age/keys.txt'
DB = 'newport-jack-auth-db-1'
DATA = 'zitadel.dump.age'
RECEIPT = 'infra-zitadel-v1.json'
STAMP = '%Y%m%dT%H%M%S%fZ'
CONFIG = Path(__file__).resolve().parent / 'secrets'
DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


def capture(*args):
    return subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL).strip()


def mount_id(fd):
    return re.search(r'^mnt_id:\s+(\d+)$', Path(f'/proc/self/fdinfo/{fd}').read_text(), re.M)[1]


def enter_store(create):
    fd = os.open(MOUNT, DIR_FLAGS)
    identity = f'{mount_id(fd)} {MOUNT} {SOURCE} nfs4'
    if identity not in capture('findmnt', '-n', '-M', MOUNT, '-o', 'ID,TARGET,SOURCE,FSTYPE').splitlines():
        raise RuntimeError('unexpected or missing Stash NFS mount')
    if create:
        try:
            os.mkdir(STORE, mode=0o700, dir_fd=fd)
        except FileExistsError:
            pass
    dest = os.open(STORE, DIR_FLAGS, dir_fd=fd)
    if mount_id(dest) != mount_id(fd) or os.fstat(dest).st_uid != os.getuid() or os.fstat(dest).st_mode & 0o077:
        raise RuntimeError('unexpected backup directory identity or permissions')
    os.fchdir(dest)
    os.close(dest)
    os.close(fd)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verified(path):
    try:
        if path.is_symlink() or not path.is_dir() or {p.name for p in path.iterdir()} != {DATA, RECEIPT}:
            return False
        if any(p.is_symlink() or not p.is_file() for p in (path / DATA, path / RECEIPT)):
            return False
        meta = json.loads((path / RECEIPT).read_text())
        return (meta['generation'] == path.name and meta['format'] == RECEIPT
                and meta['sha256'] == digest(path / DATA))
    except (ValueError, KeyError, TypeError, FileNotFoundError):
        return False


def generations():
    for path in sorted(Path('.').iterdir(), reverse=True):
        if not re.fullmatch(r'\d{8}T\d{12}Z', path.name):
            continue
        try:
            stamp = datetime.strptime(path.name, STAMP).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if verified(path):
            yield path, stamp
        else:
            print(f'Preserving unverified generation {path}', flush=True)


def retain():
    days, weeks = set(), set()
    for path, stamp in generations():
        day = stamp.date()
        week = day.isocalendar()[:2]
        daily = day not in days and len(days) < 7
        weekly = week not in weeks and len(weeks) < 4
        if daily:
            days.add(day)
        if weekly:
            weeks.add(week)
        if not daily and not weekly:
            # Remove only the two verified files, leaving anything unexpected alone.
            (path / RECEIPT).unlink()
            (path / DATA).unlink()
            path.rmdir()


def pipe(producer, consumer, **output):
    with subprocess.Popen(producer, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as src:
        try:
            result = subprocess.run(consumer, stdin=src.stdout, stderr=subprocess.DEVNULL, **output)
        finally:
            src.stdout.close()
        if src.wait() or result.returncode:
            raise RuntimeError('dump/encrypt or decrypt/restore pipeline failed')


def restore(path, image):
    if capture('age-keygen', '-y', str(IDENTITY)) != RECIPIENT:
        raise RuntimeError('recovery identity does not match the configured recipient')
    start = time.monotonic()
    name = f'jack-auth-restore-{uuid.uuid4().hex}'
    try:
        capture('docker', 'run', '--detach', '--rm', '--pull=never', '--name', name, '--network', 'none',
                '--memory', '512m', '--cpus', '1', '--tmpfs', '/var/lib/postgresql/data:rw,size=512m',
                '-e', 'POSTGRES_USER=zitadel', '-e', 'POSTGRES_DB=zitadel',
                '-e', 'POSTGRES_HOST_AUTH_METHOD=trust', image, 'postgres', '-c', 'listen_addresses=')
        for _ in range(45):
            # Wait for the final PID 1 server, not the temporary init server.
            if subprocess.run(['docker', 'exec', name, 'sh', '-c',
                               '[ "$(cat /proc/1/comm)" = postgres ] && pg_isready -U zitadel -d zitadel'],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
                break
            time.sleep(1)
        else:
            raise RuntimeError('isolated Postgres did not become ready')
        pipe(['age', '-d', '-i', str(IDENTITY), str(path)],
             ['docker', 'exec', '-i', name, 'pg_restore', '--exit-on-error', '-U', 'zitadel', '-d', 'zitadel'],
             stdout=subprocess.DEVNULL)
        count = int(capture('docker', 'exec', name, 'psql', '-XAt', '-U', 'zitadel', '-d', 'zitadel',
                            '-c', 'select count(*) from eventstore.events2'))
        if not count:
            raise RuntimeError('restored eventstore is empty')
        print(f'Isolated restore passed: {count} events in {time.monotonic() - start:.1f}s', flush=True)
    finally:
        subprocess.run(['docker', 'rm', '-f', '-v', name], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, check=False)


def backup(first):
    if capture('docker', 'inspect', '--format', '{{.Name}} {{index .Config.Labels "com.docker.compose.service"}}', DB) != f'/{DB} jack-auth-db':
        raise RuntimeError('unexpected source container')
    roles = capture('docker', 'exec', DB, 'psql', '-XAt', '-U', 'zitadel', '-d', 'zitadel', '-c',
                    "select rolname,rolsuper,rolcanlogin from pg_roles where rolname !~ '^pg_'")
    if roles != 'zitadel|t|t':
        raise RuntimeError('Postgres recovery role contract changed; review before backing up')
    if not first and not next(generations(), None):
        raise RuntimeError('no verified baseline; run the isolated first-run procedure')
    stage = Path(tempfile.mkdtemp(prefix='.partial-', dir='.'))
    try:
        stamp = datetime.now(timezone.utc).strftime(STAMP)
        image = capture('docker', 'inspect', '--format', '{{.Image}}', DB)
        with (stage / DATA).open('xb') as out:
            pipe(['docker', 'exec', DB, 'pg_dump', '-w', '-U', 'zitadel', '-d', 'zitadel',
                  '--format=custom', '--compress=6', '--lock-wait-timeout=5s'],
                 ['age', '-r', RECIPIENT], stdout=out)
            out.flush()
            os.fsync(out.fileno())
        meta = {'format': RECEIPT, 'generation': stamp, 'sha256': digest(stage / DATA),
                'postgres_image': image, 'recipient': RECIPIENT,
                'encrypted_config_sha256': {name: digest(CONFIG / name) for name in
                                            ('postgres.enc.yaml', 'zitadel.enc.yaml', 'smtp.enc.yaml')}}
        if first:
            restore(stage / DATA, image)
        with (stage / RECEIPT).open('x') as out:
            json.dump(meta, out, indent=2)
            out.write('\n')
            out.flush()
            os.fsync(out.fileno())
        os.rename(stage, stamp)
        if not verified(Path(stamp)):
            raise RuntimeError('published checksum failed readback')
        print(f'Published {stamp}: {(Path(stamp) / DATA).stat().st_size} bytes, SHA-256 {meta["sha256"]}', flush=True)
        if not first:
            retain()
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('backup', 'first', 'check'))
    mode = parser.parse_args().mode
    os.umask(0o077)
    enter_store(mode == 'first')
    if mode == 'check':
        newest = next(generations(), None)
        if newest is None or not timedelta(0) <= datetime.now(timezone.utc) - newest[1] <= timedelta(hours=30):
            raise RuntimeError('STALE: no verified ZITADEL backup within 30 hours')
        print(f'Fresh verified ZITADEL generation: {newest[0]}')
        return
    with (Path(os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}')) / 'jack-auth-provider-backup.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        backup(mode == 'first')


if __name__ == '__main__':
    main()

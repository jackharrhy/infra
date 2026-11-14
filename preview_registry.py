"""Small, trusted local preview registry; not a same-UID security sandbox."""
from __future__ import annotations

import fcntl
import json
import os
import re
import socket
import subprocess
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit

import click
import yaml

ROOT = Path(__file__).resolve().parent
STATE = Path.home() / '.local/state/infra/previews'
DYNAMIC = ROOT / 'hosts/newport/traefik/dynamic'
PROJECTION = 'previews.runtime.yml'
SUFFIX = '.pi.jackharrhy.dev'
DEFAULT_TTL = 86400
MAX_TTL = 7 * DEFAULT_TTL
RESERVED = {'pi', 'auth', 'api', 'admin', 'login', 'mcp', 'traefik',
            'alderpoint', 'alderpoint-api', '4orm', 'wonder', 'browse'}
# Permanent native/administrative listeners not all represented in Compose.
PROTECTED = {8788, 18081, 18085, 18086, 18955, 19004, 19005, 19006, 19988, 19989}
FIELDS = {'owner', 'purpose', 'port', 'paths', 'prefixes', 'expires_at'}


def ttl_seconds(value):
    match = re.fullmatch(r'([1-9][0-9]*)([mhd])', value)
    if not match:
        raise ValueError('TTL must be a positive duration such as 30m, 24h or 7d')
    seconds = int(match[1]) * {'m': 60, 'h': 3600, 'd': 86400}[match[2]]
    if seconds > MAX_TTL:
        raise ValueError('Maximum lease is 7d')
    return seconds


def loopback_listener(port):
    result = subprocess.run(['ss', '-H', '-ltn'], check=True, capture_output=True, text=True)
    addresses = []
    for line in result.stdout.splitlines():
        local = line.split()[3]
        address, number = local.rsplit(':', 1)
        if number == str(port):
            addresses.append(address)
    if '127.0.0.1' not in addresses or any(a not in {'127.0.0.1', '[::1]', '::1'} for a in addresses):
        raise ValueError('Target must already listen on loopback only (not 0.0.0.0, LAN or Tailnet)')


def atomic_write(path, data):
    """Directory-mounted projection: replace its inode, never a single-file bind."""
    fd, name = tempfile.mkstemp(prefix='.preview-', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
        directory = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def check_record(name, entry):
    if not isinstance(name, str) or not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', name) or name in RESERVED:
        raise ValueError(f'Invalid or reserved preview name: {name}')
    if not isinstance(entry, dict) or set(entry) != FIELDS:
        raise ValueError('Invalid registry record fields')
    if not isinstance(entry['owner'], str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:@/-]{0,127}', entry['owner']):
        raise ValueError('Invalid owner label')
    purpose = entry['purpose']
    if not isinstance(purpose, str) or not 1 <= len(purpose) <= 200 or any(ord(c) < 32 for c in purpose):
        raise ValueError('Purpose must be 1-200 printable characters')
    if type(entry['port']) is not int or not 1024 <= entry['port'] <= 65535:
        raise ValueError('Port must be an unprivileged integer TCP port')
    if type(entry['expires_at']) is not int or entry['expires_at'] <= 0:
        raise ValueError('Invalid lease expiry')
    for key in ['paths', 'prefixes']:
        values = entry[key]
        if not isinstance(values, list) or len(values) > 16:
            raise ValueError('At most 16 exact paths/prefixes each')
        for value in values:
            if not isinstance(value, str) or not re.fullmatch(r'/[A-Za-z0-9/_.-]*', value) or '..' in value:
                raise ValueError('Paths must be literal URL paths, not expressions/queries/filesystem paths')
            if key == 'prefixes' and not value.endswith('/'):
                raise ValueError('Asset prefixes must end in /')


def route(name, entry):
    rule = f'Host(`{name}{SUFFIX}`)'
    paths = [f'Path(`{p}`)' for p in entry['paths']]
    paths += [f'PathPrefix(`{p}`)' for p in entry['prefixes']]
    if paths:
        rule += ' && (' + ' || '.join(paths) + ')'
    return {'rule': rule, 'entryPoints': ['pitailnet'],
            'service': f'temp-preview-{name}', 'tls': {}}


def service(entry):
    return {'loadBalancer': {'passHostHeader': True,
                            'servers': [{'url': f'http://127.0.0.1:{entry["port"]}'}]}}


class Registry:
    def __init__(self, state=STATE, dynamic=DYNAMIC, compose=None, clock=time.time, listener=loopback_listener):
        self.state = Path(state)
        self.dynamic = Path(dynamic)
        self.compose = Path(compose) if compose else ROOT / 'hosts/newport/compose.yml'
        self.clock = clock
        self.listener = listener

    @contextmanager
    def locked(self):
        self.state.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.state.is_symlink() or self.dynamic.is_symlink():
            raise ValueError('Registry/projection directories must not be symlinks')
        os.chmod(self.state, 0o700)
        with open(self.state / 'lock', 'a') as lock:
            os.chmod(self.state / 'lock', 0o600)
            fcntl.flock(lock, fcntl.LOCK_EX)
            yield

    def read(self):
        path = self.state / 'registry.json'
        if not path.exists():
            return {}
        data = json.loads(path.read_text())
        if not isinstance(data, dict) or set(data) != {'version', 'leases'} or type(data['version']) is not int or data['version'] != 1 or not isinstance(data['leases'], dict):
            raise ValueError('Invalid registry schema; last-good projection left untouched')
        for name, entry in data['leases'].items():
            check_record(name, entry)
        return data['leases']

    def static(self):
        routers, services = {}, {}
        for path in sorted(self.dynamic.glob('*')):
            if path.name == PROJECTION or path.suffix not in {'.yaml', '.yml', '.toml'}:
                continue
            if path.suffix == '.toml':
                import tomllib
                data = tomllib.loads(path.read_text())
            else:
                data = yaml.safe_load(path.read_text()) or {}
            http = data.get('http', {})
            for dest, key in [(routers, 'routers'), (services, 'services')]:
                for name, value in http.get(key, {}).items():
                    if name.startswith('temp-preview-') or name in dest:
                        raise ValueError('Static configuration collides with preview namespace')
                    dest[name] = value
        ports = set(PROTECTED)
        compose = yaml.safe_load(self.compose.read_text())
        for item in compose.get('services', {}).values():
            for mapping in item.get('ports', []):
                if isinstance(mapping, dict):
                    published = str(mapping.get('published', ''))
                else:
                    pieces = str(mapping).split(':')
                    published = pieces[-2] if len(pieces) > 1 else ''
                if published.isdigit():
                    ports.add(int(published))
        return routers, services, ports

    def validate(self, leases, new_name=None, adopt=False):
        routers, services, protected = self.static()
        used = set()
        for name, entry in leases.items():
            check_record(name, entry)
            if entry['expires_at'] > int(self.clock()) + MAX_TTL:
                raise ValueError('Lease is more than 7d in the future')
            if entry['port'] in protected or entry['port'] in used:
                raise ValueError('Protected or already leased port')
            used.add(entry['port'])
            expected = route(name, entry)
            for router in routers.values():
                if f'{name}{SUFFIX}' not in router.get('rule', ''):
                    continue
                existing = dict(router)
                target = existing.pop('service', None)
                comparable = dict(expected)
                comparable.pop('service')
                equivalent = existing == comparable and services.get(target) == service(entry)
                if not equivalent or (name == new_name and not adopt):
                    raise ValueError('Hostname already has a static route; only exact-equivalent adoption is allowed')
            # Include localhost/IPv6 aliases and path-bearing permanent URLs.
            targets = [r.get('service') for r in routers.values()
                       if f'{name}{SUFFIX}' in r.get('rule', '')]
            for key, existing in services.items():
                for server in existing.get('loadBalancer', {}).get('servers', []):
                    url = urlsplit(server.get('url', ''))
                    if url.hostname in {'127.0.0.1', 'localhost', '::1'} and url.port == entry['port']:
                        if key not in targets or existing != service(entry):
                            raise ValueError('Port belongs to a permanent static service')

    def commit(self, leases):
        rendered = {'http': {'routers': {}, 'services': {}}}
        for name, entry in sorted(leases.items()):
            rendered['http']['routers'][f'temp-preview-{name}'] = route(name, entry)
            rendered['http']['services'][f'temp-preview-{name}'] = service(entry)
        projection = yaml.safe_dump(rendered, sort_keys=False).encode()
        registry = (json.dumps({'version': 1, 'leases': leases}, indent=2) + '\n').encode()
        path = self.state / 'registry.json'
        previous = path.read_bytes() if path.exists() else None
        target = self.dynamic / PROJECTION
        if previous == registry and target.exists() and target.read_bytes() == projection:
            return  # Do not trigger provider reloads for unchanged minutely sweeps.
        self.dynamic.mkdir(parents=True, exist_ok=True)
        atomic_write(path, registry)
        try:
            atomic_write(self.dynamic / PROJECTION, projection)
        except Exception:
            if previous is None:
                path.unlink(missing_ok=True)
            else:
                atomic_write(path, previous)
            raise

    def apply(self, operation, name=None, owner=None, ttl=DEFAULT_TTL, port=None,
              purpose=None, paths=(), prefixes=(), adopt=False):
        if type(ttl) is not int or not 60 <= ttl <= MAX_TTL:
            raise ValueError('Lease must be between 1m and 7d')
        with self.locked():
            original = self.read()
            now = int(self.clock())
            leases = {k: v for k, v in original.items() if v['expires_at'] > now}
            expired = sorted(set(original) - set(leases))
            if operation in {'register', 'renew', 'remove'}:
                existing = leases.get(name)
                if existing and existing['owner'] != owner:
                    raise ValueError('Lease belongs to another owner; no takeover')
                if operation in {'renew', 'remove'} and not existing:
                    raise ValueError('No active lease with that name')
                if operation == 'register':
                    leases[name] = {'owner': owner, 'purpose': purpose, 'port': port,
                                    'paths': list(paths), 'prefixes': list(prefixes), 'expires_at': now + ttl}
                    check_record(name, leases[name])
                    self.listener(port)
                elif operation == 'renew':
                    leases[name] = {**existing, 'expires_at': now + ttl}
                    self.listener(existing['port'])
                else:
                    del leases[name]
            elif operation != 'reconcile':
                raise ValueError('Unknown operation')
            self.validate(leases, new_name=name if operation == 'register' else None, adopt=adopt)
            self.commit(leases)
            return leases, expired


@click.group()
def preview():
    """Newport-only temporary Tailnet routes. Does not start/stop applications."""
    if socket.gethostname().split('.')[0] != 'newport':
        raise click.ClickException('Run this command on Newport, not a remote checkout')


def run(operation, **kwargs):
    try:
        leases, expired = Registry().apply(operation, **kwargs)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        raise click.ClickException(str(error)) from error
    if expired:
        click.echo('Expired routes removed: ' + ', '.join(expired))
    if kwargs.get('name') in leases:
        name = kwargs['name']
        click.echo(f'https://{name}{SUFFIX} (expires {time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(leases[name]["expires_at"]))})')
    else:
        click.echo(f'{operation}: {len(leases)} active temporary routes')


@preview.command()
@click.argument('name')
@click.option('--port', required=True, type=int)
@click.option('--owner', required=True)
@click.option('--purpose', required=True)
@click.option('--ttl', default='24h', show_default=True)
@click.option('--path', 'paths', multiple=True, help='Optional literal exact URL path')
@click.option('--prefix', 'prefixes', multiple=True, help='Optional literal URL prefix ending in /')
@click.option('--adopt-existing', is_flag=True, help='One-time exact-equivalent static route migration only')
def register(name, port, owner, purpose, ttl, paths, prefixes, adopt_existing):
    try:
        seconds = ttl_seconds(ttl)
    except ValueError as error:
        raise click.ClickException(str(error)) from error
    run('register', name=name, port=port, owner=owner, purpose=purpose, ttl=seconds,
        paths=paths, prefixes=prefixes, adopt=adopt_existing)


@preview.command()
@click.argument('name')
@click.option('--owner', required=True)
@click.option('--ttl', default='24h', show_default=True)
def renew(name, owner, ttl):
    try:
        seconds = ttl_seconds(ttl)
    except ValueError as error:
        raise click.ClickException(str(error)) from error
    run('renew', name=name, owner=owner, ttl=seconds)


@preview.command()
@click.argument('name')
@click.option('--owner', required=True)
def remove(name, owner):
    run('remove', name=name, owner=owner)


@preview.command('list')
def list_previews():
    try:
        registry = Registry()
        with registry.locked():
            leases = registry.read()
        now = int(time.time())
        for name, entry in sorted(leases.items()):
            remaining = max(0, entry['expires_at'] - now)
            click.echo(f'{name}\t{entry["owner"]}\t127.0.0.1:{entry["port"]}\t{remaining}s\t{entry["purpose"]}')
    except (ValueError, OSError) as error:
        raise click.ClickException(str(error)) from error


@preview.command()
def reconcile():
    """Expire leases and rebuild projection (startup/minutely timer)."""
    run('reconcile')

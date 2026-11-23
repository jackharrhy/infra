#!/usr/bin/python3
"""GET-only native account snapshots; credentials never leave this process."""
import datetime
import fcntl
import json
import os
from pathlib import Path
import tempfile
import urllib.request

ROOT = Path.home() / '.local/state/infra/media-inventory'
SETTINGS = Path('/mnt/terrabud/docker-data/newport/seerr/settings.json')
LIMIT = 1024 * 1024


def integer(value):
    if type(value) is not int or not 0 <= value <= 9007199254740991:
        raise ValueError('Invalid integer')
    return value


def name(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 200:
        raise ValueError('Invalid native name')
    return value


def jellyfin(rows):
    result = []
    for row in rows:
        policy = row['Policy']
        if any(type(policy[k]) is not bool for k in ('IsDisabled', 'IsAdministrator')):
            raise ValueError('Invalid policy')
        result.append(dict(nativeId=name(row['Id']), name=name(row['Name']),
                           disabled=policy['IsDisabled'], administrator=policy['IsAdministrator']))
    return result


def seerr(rows):
    result = []
    for row in rows:
        uid, permissions = integer(row['id']), integer(row['permissions'])
        # Seerr has no native disabled state. This is not a sign-in guarantee.
        result.append(dict(nativeId=str(uid), name=name(row.get('displayName') or row.get('username')),
                           disabled=False, administrator=uid == 1 or bool(permissions & 2)))
    return result


def envelope(service, accounts):
    if len(accounts) > 10000 or len({a['nativeId'] for a in accounts}) != len(accounts):
        raise ValueError('Invalid roster')
    return dict(service=service, instance='newport', state='available',
                observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(), accounts=accounts)


def get(url, headers):
    # Never follow a redirect carrying a server API key.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with opener.open(urllib.request.Request(url, headers=headers, method='GET'), timeout=5) as response:
        data = response.read(LIMIT + 1)
    if len(data) > LIMIT:
        raise ValueError('Oversized response')
    return json.loads(data)


def seerr_pages(key):
    rows = []
    total = None
    for skip in range(0, 10000, 100):
        page = get(f'http://127.0.0.1:5055/api/v1/user?take=100&skip={skip}', {'X-Api-Key': key})
        count = integer(page['pageInfo']['results'])
        batch = page['results']
        if count > 10000 or (total is not None and total != count) or not isinstance(batch, list) or len(batch) > 100:
            raise ValueError('Invalid pagination')
        total = count
        rows.extend(batch)
        if len(rows) == total:
            return rows
        if not batch or len(rows) > total or len(batch) != 100:
            raise ValueError('Incomplete pagination')
    raise ValueError('Pagination limit')


def atomic(path, value):
    data = json.dumps(value, ensure_ascii=False).encode()
    if len(data) > LIMIT:
        raise ValueError('Oversized snapshot')
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.snapshot-')
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main():
    os.umask(0o077)
    ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (ROOT / '.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        settings = json.loads(SETTINGS.read_text())
        failed = False
        for service in ('jellyfin', 'seerr'):
            try:
                if service == 'jellyfin':
                    key = settings['jellyfin']['apiKey']
                    rows = jellyfin(get('http://127.0.0.1:8096/Users', {'Authorization':
                        f'MediaBrowser Client="Infra", Device="Operator", DeviceId="infra-readonly", Version="1", Token="{key}"'}))
                else:
                    rows = seerr(seerr_pages(settings['main']['apiKey']))
                atomic(ROOT / f'{service}.json', envelope(service, rows))
                print(f'{service}: refreshed ({len(rows)} accounts)')
            except Exception:
                # Do not leak URLs, credentials, native payloads or exception details.
                print(f'{service}: refresh failed; previous observation retained')
                failed = True
        atomic(ROOT / 'instances.json', [dict(service=s, instance='newport', name=s.title(),
               snapshotFile=f'/run/media-inventory/{s}.json') for s in ('jellyfin', 'seerr')])
        return int(failed)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception:
        print('Inventory refresh failed')
        raise SystemExit(1)

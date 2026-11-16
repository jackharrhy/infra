#!/usr/bin/env python3
"""Offline proposal renderer; never inspects Docker or writes outside output directory."""
import argparse
import json
from pathlib import Path
import re
import yaml


def build(inventory):
    host = inventory['host']
    if host not in ('newport', 'mug'):
        raise ValueError('host must be newport or mug')
    selected = inventory['services']
    if not selected:
        raise ValueError('explicit nonempty services required')
    cap_services = inventory.get('cap_services', [])
    if not isinstance(cap_services, list) or any(not isinstance(s, str) or s not in selected for s in cap_services):
        raise ValueError('cap_services must be a list drawn from selected services')
    # Exclude already capped services until their effective configuration is compared.
    # Explicit selection acknowledges that these proposed values may loosen tighter caps.
    vector = {'data_dir': '/var/lib/vector', 'sources': {}, 'transforms': {}, 'sinks': {}, 'tests': []}
    mounts = ['./vector.yaml:/etc/vector/vector.yaml:ro', 'vector-data:/var/lib/vector']
    caps = {'services': {}}
    seen = set()
    for service, cid in selected.items():
        if not re.fullmatch(r'[a-z][a-z0-9_-]{0,62}', service):
            raise ValueError('service must be a simple component identifier')
        if not re.fullmatch(r'[0-9a-f]{64}', cid) or cid in seen:
            raise ValueError('unique full container IDs required')
        seen.add(cid)
        # Only the selected container directory, never the Docker root or socket.
        mounts.append({'type': 'bind', 'source': f'/var/lib/docker/containers/{cid}',
                       'target': f'/input/{service}', 'read_only': True,
                       'bind': {'create_host_path': False}})
        vector['sources'][service] = {'type': 'file', 'include': [f'/input/{service}/{cid}-json.log*'],
                                     'read_from': 'end', 'max_line_bytes': 262144}
        # No arbitrary log payload survives. Deliberately conservative baseline.
        vector['transforms']['safe_' + service] = {
            'type': 'remap', 'inputs': [service], 'drop_on_error': True,
            'drop_on_abort': True, 'source': f'''raw = parse_json!(string!(.message))
ts = parse_timestamp!(string!(raw.time), format: "%+")
stream = string!(raw.stream)
if stream != "stdout" && stream != "stderr" {{ abort }}
. = {{"_time": ts, "_msg": "[redacted]", "host": "{host}", "service": "{service}", "stream": stream}}
'''}
        vector['tests'].extend([
            {'name': f'{service}_redacts_secret_payload',
             'inputs': [{'insert_at': 'safe_' + service, 'type': 'raw',
                         'value': json.dumps({'time': '2026-11-17T00:00:00Z', 'stream': 'stderr',
                                             'log': 'Authorization: Bearer SYNTHETIC password=FIXTURE email=fake@example.invalid',
                                             'unknown': 'SYNTHETIC_SECRET'})}],
             'outputs': [{'extract_from': 'safe_' + service,
                          'conditions': [{'type': 'vrl', 'source': f'''assert_eq!(., {{"_time": t'2026-11-17T00:00:00Z', "_msg": "[redacted]", "host": "{host}", "service": "{service}", "stream": "stderr"}})
true'''}]}]},
            {'name': f'{service}_drops_invalid_stream',
             'inputs': [{'insert_at': 'safe_' + service, 'type': 'raw',
                         'value': json.dumps({'time': '2026-11-17T00:00:00Z', 'stream': 'not-a-docker-stream',
                                             'log': 'SYNTHETIC_SECRET'})}],
             'no_outputs_from': ['safe_' + service]},
        ])
        if service in cap_services:
            caps['services'][service] = {'logging': {'driver': 'json-file', 'options': {'max-size': '10m', 'max-file': '3'}}}
    vector['sinks']['central'] = {
        'type': 'http', 'inputs': ['safe_' + s for s in selected],
        'uri': 'https://${LOG_WRITE_HOST:?private ingress required}/insert/jsonline?_stream_fields=host,service,stream&_time_field=_time&_msg_field=_msg',
        'method': 'post', 'compression': 'gzip',
        'encoding': {'codec': 'json'}, 'framing': {'method': 'newline_delimited'},
        'request': {'headers': {'Content-Type': 'application/stream+json'}},
        'auth': {'strategy': 'basic', 'user': host, 'password': '${LOG_WRITE_PASSWORD:?per-host write credential required}'},
        'tls': {'verify_certificate': True, 'verify_hostname': True},
        'healthcheck': {'enabled': False},
        'buffer': {'type': 'disk', 'max_size': 268435488, 'when_full': 'block'}}
    compose = {'services': {'vector': {
        'image': 'timberio/vector:0.62.0-debian@sha256:6266b1d35c844918ff1c48ea2ec4f57c2b0664c46f3e17fc2418d5dda1692068', 'command': ['--config', '/etc/vector/vector.yaml', '--dangerously-allow-env-var-interpolation'],
        'restart': 'unless-stopped', 'volumes': mounts,
        'environment': {'LOG_WRITE_HOST': '${LOG_WRITE_HOST:?required}', 'LOG_WRITE_PASSWORD': '${LOG_WRITE_PASSWORD:?required}'},
        'logging': {'driver': 'json-file', 'options': {'max-size': '10m', 'max-file': '3'}}}},
        'volumes': {'vector-data': {}}}
    return vector, compose, caps


def main():
    p = argparse.ArgumentParser()
    p.add_argument('inventory', type=Path)
    p.add_argument('output', type=Path)
    a = p.parse_args()
    vector, compose, caps = build(json.loads(a.inventory.read_text()))
    a.output.mkdir(parents=True, exist_ok=True)
    for name, value in [('vector.yaml', vector), ('compose.yaml', compose)]:
        (a.output / name).write_text(yaml.safe_dump(value, sort_keys=False))
    cap_path = a.output / 'logging-caps.override.yaml'
    if caps['services']:
        cap_path.write_text(yaml.safe_dump(caps, sort_keys=False))
    else:
        # Remove only our named generated artifact when re-rendering without caps.
        cap_path.unlink(missing_ok=True)

if __name__ == '__main__':
    main()

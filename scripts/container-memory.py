#!/usr/bin/env python3
"""Report running containers' cgroup-v2 memory and swap without changing them."""

import argparse
import json
from pathlib import Path
import subprocess
import sys


def memory_usage(proc, cgroups, pid):
    entries = (proc / str(pid) / 'cgroup').read_text().splitlines()
    relative = next((line[3:] for line in entries if line.startswith('0::')), None)
    if relative is None:
        raise ValueError('requires a unified cgroup-v2 hierarchy')
    directory = (cgroups / relative.lstrip('/')).resolve()
    if not directory.is_relative_to(cgroups.resolve()):
        raise ValueError('cgroup path is outside the mounted hierarchy')
    return {
        'memory': int((directory / 'memory.current').read_text()),
        'swap': int((directory / 'memory.swap.current').read_text()),
        'limit': (directory / 'memory.max').read_text().strip(),
    }


def docker(*args):
    return subprocess.check_output(['docker', *args], text=True, timeout=30)


def mib(value):
    return f'{value / 1048576:.1f}'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', help='only this Compose project')
    args = parser.parse_args()
    filters = ['--filter', f'label=com.docker.compose.project={args.project}'] if args.project else []
    ids = docker('ps', '-q', *filters).split()
    if not ids:
        print('No running containers match.')
        return 0
    containers = json.loads(docker('inspect', *ids))
    rows, errors = [], []
    for container in containers:
        name = container['Name'].lstrip('/')
        try:
            usage = memory_usage(Path('/proc'), Path('/sys/fs/cgroup'), container['State']['Pid'])
            rows.append({'name': name, **usage})
        except (OSError, ValueError) as error:
            errors.append(f'{name}: {error}')
    print(f'{"CONTAINER":32} {"RAM MiB":>10} {"SWAP MiB":>10} {"SUM MiB":>10} {"RAM CAP MiB":>12}')
    for row in sorted(rows, key=lambda row: row['memory'] + row['swap'], reverse=True):
        cap = 'unlimited' if row['limit'] == 'max' else mib(int(row['limit']))
        print(f'{row["name"]:32} {mib(row["memory"]):>10} {mib(row["swap"]):>10} '
              f'{mib(row["memory"] + row["swap"]):>10} {cap:>12}')
    print(f'{"TOTAL (reported containers)":32} {mib(sum(row["memory"] for row in rows)):>10} '
          f'{mib(sum(row["swap"] for row in rows)):>10}')
    print('RAM is memory.current (includes charged cache), not RSS. Swap occupancy alone is not paging activity.')
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        print('Report is incomplete; try sudo and check for containers exiting during collection.', file=sys.stderr)
    return 1 if errors else 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, subprocess.SubprocessError, ValueError) as error:
        sys.exit(str(error))


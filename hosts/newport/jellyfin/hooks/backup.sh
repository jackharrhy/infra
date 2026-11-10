#!/bin/sh
set -eu

marker=/config/.infra/last-backup
if [ "${1:-daily}" = daily ] && [ -f "$marker" ] && [ -n "$(find "$marker" -mtime -1 -print)" ]; then
    exit 0
fi

if ! curl --config /config/.infra/backup.curl --fail --silent --show-error \
    --max-time 300 --output /dev/null http://127.0.0.1:8096/Backup/Create; then
    echo 'Jellyfin native backup failed; refusing an unprotected update.' >&2
    exit 75
fi
touch "$marker"
echo 'Jellyfin native backup completed.'

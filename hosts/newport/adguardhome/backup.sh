#!/bin/sh
set -eu
umask 077
source=${CONFIG_FILE:-/opt/adguardhome/conf/AdGuardHome.yaml}
backups=${BACKUP_DIR:-/backups}
helper=${INFRA_BACKUP_HELPER:-/opt/infra-backup-retention.sh}
test -s "$source"
mkdir -p "$backups"
if [ "${1:-}" = daily ] && [ -f "$backups/.last-success" ] && find "$backups/.last-success" -mtime -1 | grep -q .; then
    printf '%s\n' 'Recent AdGuard Home configuration backup retained'
    exit 0
fi
temporary=$(mktemp "$backups/.incomplete.XXXXXX")
trap 'rm -f "$temporary"' EXIT INT TERM
cp "$source" "$temporary"
chmod 600 "$temporary"
cmp -s "$source" "$temporary"
previous=
if [ "${1:-}" != manual ]; then
    digest=$(sh "$helper" hash "$temporary")
    previous=$(sh "$helper" reuse "$backups" "$digest")
fi
name="$(date -u +%Y%m%dT%H%M%SZ)-$$.yaml"
if [ -n "$previous" ]; then
    name=$previous
    rm "$temporary"
    printf "%s\n" "Fresh AdGuard configuration matches verified previous publication"
else
    mv "$temporary" "$backups/$name"
    if [ "${1:-}" != manual ]; then
        sh "$helper" complete "$backups" "$name" "$digest"
    fi
fi
printf '%s\n' "$name" > "$backups/.last-success.new"
mv "$backups/.last-success.new" "$backups/.last-success"
printf 'AdGuard Home configuration backup complete: %s\n' "$name"

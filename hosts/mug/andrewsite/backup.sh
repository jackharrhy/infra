#!/usr/bin/env bash
set -euo pipefail
umask 077

tea_source=/home/jack/infra/hosts/mug/volumes/andrewsite_tea_data
tea_backups=/home/jack/backups/andrewsite
test -f "$tea_source/tea.db"
test -d "$tea_source/uploads"
mkdir -p "$tea_backups"
exec 9>"$tea_backups/.backup.lock"
flock -n 9 || exit 0

tea_snapshot=$(mktemp -d "$tea_backups/.snapshot-XXXXXX")
tea_archive="$tea_backups/tea-$(date -u +%Y%m%dT%H%M%SZ).tar.gz"
# Media is unlisted rather than physically deleted, so a DB-first snapshot
# retains all files referenced by that point in time while editing continues.
sqlite3 -readonly "$tea_source/tea.db" ".backup '$tea_snapshot/tea.db'"
cp -a "$tea_source/uploads" "$tea_snapshot/uploads"
test "$(sqlite3 -readonly "$tea_snapshot/tea.db" 'PRAGMA integrity_check;')" = ok
tar -czf "$tea_archive" -C "$tea_snapshot" tea.db uploads
tar -tzf "$tea_archive" >/dev/null
case "$tea_snapshot" in
  "$tea_backups"/.snapshot-*) rm -r -- "$tea_snapshot" ;;
  *) exit 1 ;;
esac
find "$tea_backups" -maxdepth 1 -type f -name 'tea-????????T??????Z.tar.gz' -mtime +13 -delete
printf 'TeaCMS backup verified: %s\n' "$tea_archive"

#!/usr/bin/env bash
set -euo pipefail
umask 077

tea_source=/home/jack/infra/hosts/mug/volumes/teacms
tea_backups=/home/jack/backups/teacms
mkdir -p "$tea_backups"
exec 9>"$tea_backups/.backup.lock"
flock -n 9 || exit 0

tea_snapshot=$(mktemp -d "$tea_backups/.snapshot-XXXXXX")
trap 'rm -rf -- "$tea_snapshot"' EXIT
tea_archive="$tea_backups/tea-$(date -u +%Y%m%dT%H%M%SZ).tar.gz"
for site in andrew luke; do
  source_dir="$tea_source/$site"
  test -f "$source_dir/tea.db"
  mkdir -p "$tea_snapshot/$site"
  sqlite3 -readonly "$source_dir/tea.db" ".backup '$tea_snapshot/$site/tea.db'"
  test "$(sqlite3 -readonly "$tea_snapshot/$site/tea.db" 'PRAGMA integrity_check;')" = ok
  for directory in uploads public; do
    if test -d "$source_dir/$directory"; then
      cp -a "$source_dir/$directory" "$tea_snapshot/$site/$directory"
    fi
  done
done
mkdir -p "$tea_snapshot/operator"
test -f "$tea_source/operator/operator.db"
sqlite3 -readonly "$tea_source/operator/operator.db" ".backup '$tea_snapshot/operator/operator.db'"
test "$(sqlite3 -readonly "$tea_snapshot/operator/operator.db" 'PRAGMA integrity_check;')" = ok

tar -czf "$tea_archive" -C "$tea_snapshot" andrew luke operator
tar -tzf "$tea_archive" >/dev/null
find "$tea_backups" -maxdepth 1 -type f -name 'tea-????????T??????Z.tar.gz' -mtime +13 -delete
printf 'TeaCMS backup verified: %s\n' "$tea_archive"

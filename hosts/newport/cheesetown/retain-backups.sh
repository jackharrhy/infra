#!/bin/bash
set -euo pipefail
export LC_ALL=C

case "${1:---dry-run}" in
    --dry-run) apply=false ;;
    --apply|0) apply=true ;;
    [1-9]*) echo "Backup failed; retention skipped."; exit 0 ;;
    *) echo "Usage: $0 [--dry-run|--apply]" >&2; exit 2 ;;
esac

cd -- "${DEST_DIR:-/backups}"
now=${RETENTION_NOW:-$(date +%s)}
[[ $now =~ ^[0-9]+$ ]]
shopt -s nullglob
declare -A days=() weeks=()
first=true
for file in cheesetown-*.tar.gz; do
    [[ -f $file && ! -L $file ]] || continue
    [[ $file =~ ^cheesetown-([0-9]{4})([0-9]{2})([0-9]{2})-([0-9]{2})([0-9]{2})([0-9]{2})\.tar\.gz$ ]] || continue
    day="${BASH_REMATCH[1]}-${BASH_REMATCH[2]}-${BASH_REMATCH[3]}"
    stamp="$day ${BASH_REMATCH[4]}:${BASH_REMATCH[5]}:${BASH_REMATCH[6]}"
    epoch=$(date -d "$stamp" +%s)
    age=$((now - epoch))
    reason=
    if $first; then
        reason=first
        first=false
    elif (( age < 7 * 86400 )); then
        reason=recent
    elif (( age < 28 * 86400 )); then
        if [[ ! -v days[$day] ]]; then reason=daily; fi
    else
        week=$(date -d "$day" +%G-%V)
        if [[ ! -v weeks[$week] ]]; then reason=weekly; fi
    fi
    # The first archive also counts as its day's/week's representative.
    if (( age >= 7 * 86400 && age < 28 * 86400 )); then days[$day]=1; fi
    if (( age >= 28 * 86400 )); then weeks[$(date -d "$day" +%G-%V)]=1; fi
    if [[ $reason ]]; then
        printf 'KEEP %s %s\n' "$reason" "$file"
    elif $apply; then
        rm -- "$file"
        printf 'REMOVED %s\n' "$file"
    else
        printf 'WOULD_REMOVE %s\n' "$file"
    fi
done

#!/bin/sh
# hash PATH; reuse ROOT DATASET_SHA; complete ROOT BASENAME DATASET_SHA
# Call after fresh integrity-validated staging; manual producers bypass this helper.
# One writer per root; published generations must remain immutable during calls.
set -eu
export LC_ALL=C
umask 077
# Keep arbitrary artifact filenames out of diagnostics.
exec 3>&2 2>/dev/null
fail() {
    if [ "${published:-no}" = yes ]; then
        echo 'backup-retention: retention failed; completed artifact and receipt preserved' >&3
    else
        echo 'backup-retention: invalid input or operation failed' >&3
    fi
    exit 1
}
sha_ok() { [ "${#1}" = 64 ] && case $1 in *[!0-9a-f]*) return 1;; esac; }
name_ok() { case $1 in ''|[!A-Za-z0-9]*|*[!A-Za-z0-9._-]*) return 1;; esac; }
work=$(mktemp -d) || exit 1
locked=
cleanup() {
    if [ -n "$locked" ]; then
        rm -f -- "$locked/receipt"
        rmdir "$locked"
    fi
    rm -rf -- "$work"
}
trap cleanup 0
trap 'exit 1' HUP INT TERM
hash_path() (
    target=$1
    [ ! -L "$target" ] || exit 1
    if [ -f "$target" ]; then
        sha256sum < "$target" > "$work/sum" || exit 1
    elif [ -d "$target" ]; then
        # Path digests encode arbitrary filename bytes without delimiter ambiguity.
        # Include empty directories, exclude mtimes, reject links and special files.
        (cd -- "$target" && find . -exec sh -c '
            for p do
                [ ! -L "$p" ] || exit 1
                n=$(printf "%s" "$p" | sha256sum) || exit 1
                n=${n%% *}
                if [ -f "$p" ]; then
                    s=$(sha256sum < "$p") || exit 1
                    printf "f %s %s\n" "$n" "${s%% *}"
                elif [ -d "$p" ]; then
                    printf "d %s\n" "$n"
                else exit 1; fi
            done
        ' sh {} +) > "$work/manifest" || exit 1
        sort "$work/manifest" > "$work/sorted" || exit 1
        sha256sum < "$work/sorted" > "$work/sum" || exit 1
    else exit 1; fi
    read -r digest rest < "$work/sum"
    sha_ok "$digest" || exit 1
    printf '%s\n' "$digest"
)
# Fixed-order, versioned format: never source/eval receipts.
receipt() {
    [ -f "$1" ] && [ ! -L "$1" ] || return 1
    {
        IFS= read -r v && IFS= read -r b && IFS= read -r e &&
        IFS= read -r d && IFS= read -r s && IFS= read -r a || return 1
        if IFS= read -r extra || [ -n "$extra" ]; then return 1; fi
    } < "$1"
    [ "$v" = 'version=1' ] || return 1
    case $b in basename=*) b=${b#basename=};; *) return 1;; esac
    case $e in epoch=*) e=${e#epoch=};; *) return 1;; esac
    case $d in day=*) d=${d#day=};; *) return 1;; esac
    case $s in datasetSHA=*) s=${s#datasetSHA=};; *) return 1;; esac
    case $a in artifactSHA=*) a=${a#artifactSHA=};; *) return 1;; esac
    name_ok "$b" && sha_ok "$s" && sha_ok "$a" || return 1
    [ "$1" = "$meta/$b" ] || return 1
    case $e in ''|*[!0-9]*|0[0-9]*) return 1;; esac
    [ "${#e}" -le 11 ] || return 1
    [ "$(date -u -d "@$e" +%Y-%m-%d)" = "$d" ] || return 1
    [ "$e" -le "$now" ] || return 1
}
[ "$#" -ge 1 ] || fail
cmd=$1; shift
case $cmd in
hash) [ "$#" = 1 ] || fail; hash_path "$1" 2>/dev/null || fail; exit;;
reuse) [ "$#" = 2 ] || fail; root=$1; dataset=$2;;
complete) [ "$#" = 3 ] || fail; root=$1; current=$2; dataset=$3; name_ok "$current" || fail;;
*) fail;;
esac
sha_ok "$dataset" || fail
[ -d "$root" ] && [ ! -L "$root" ] || fail
root=$(cd -- "$root" && pwd -P) || fail
meta=$root/.infra-hook-v1
now=$(date -u +%s) || fail
if [ "$cmd" = reuse ] && [ ! -e "$meta" ] && [ ! -L "$meta" ]; then printf '\n'; exit; fi
[ ! -L "$meta" ] || fail
if [ ! -e "$meta" ]; then mkdir "$meta" || fail; fi
[ -d "$meta" ] || fail
mkdir "$meta/.lock" 2>/dev/null || fail
locked=$meta/.lock
if [ "$cmd" = complete ]; then
    [ ! -e "$meta/$current" ] && [ ! -L "$meta/$current" ] || fail
    artifact=$(hash_path "$root/$current" 2>/dev/null) || fail
    day=$(date -u -d "@$now" +%Y-%m-%d) || fail
    printf 'version=1\nbasename=%s\nepoch=%s\nday=%s\ndatasetSHA=%s\nartifactSHA=%s\n' \
        "$current" "$now" "$day" "$dataset" "$artifact" > "$meta/.lock/receipt" || fail
    mv -- "$meta/.lock/receipt" "$meta/$current" || fail
    published=yes
fi
: > "$work/valid"
for entry in "$meta"/*; do
    receipt "$entry" || continue
    printf '%s %s %s %s\n' "$e" "$d" "$b" "$s" >> "$work/valid"
done
sort -k1,1nr -k3,3 "$work/valid" > "$work/ordered" || fail
if [ "$cmd" = reuse ]; then
    # Only the globally newest well-formed receipt is eligible. Never cycle back
    # to an older matching capture when the latest dataset changed or is damaged.
    if read -r e d b s < "$work/ordered"; then
        if [ "$s" = "$dataset" ] && [ "$((now - e))" -le 86400 ]; then
            receipt "$meta/$b" || fail
            actual=$(hash_path "$root/$b" 2>/dev/null) || { printf '\n'; exit; }
            if [ "$actual" = "$a" ]; then printf '%s\n' "$b"; exit; fi
        fi
    fi
    printf '\n'; exit
fi
# Union newest three generations and newest on each of seven most recent UTC days.
: > "$work/days"
n=0; days=0; inspection_failed=no
while read -r e d b s; do
    n=$((n + 1)); keep=no
    [ "$n" -gt 3 ] || keep=yes
    if ! grep -qxF "$d" "$work/days"; then
        printf '%s\n' "$d" >> "$work/days"
        days=$((days + 1))
        [ "$days" -gt 7 ] || keep=yes
    fi
    [ "$b" != "$current" ] || keep=yes
    [ "$keep" = no ] || continue
    receipt "$meta/$b" || { inspection_failed=yes; continue; }
    actual=$(hash_path "$root/$b" 2>/dev/null) || { inspection_failed=yes; continue; }
    [ "$actual" = "$a" ] || { inspection_failed=yes; continue; }
    rm -rf -- "${root:?}/${b:?}" || fail
    rm -- "$meta/$b" || fail
done < "$work/ordered"
if [ "$inspection_failed" != no ]; then
    echo 'backup-retention: warning: unverifiable old generations preserved' >&3
fi

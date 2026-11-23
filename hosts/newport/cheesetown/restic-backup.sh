#!/bin/bash
set -euo pipefail
umask 077
project=$(cd -- "$(dirname -- "$0")" && pwd -P)
base=/mnt/terrabud/docker-data/newport/cheesetown
state=$base/.restic-work
credentials=$HOME/.config/cheesetown-restic/password
mount=/mnt/stash/newport
recipient=age1pxvmxa7pqmaxsxhhe7d9rfs2glaqtzxkpkmhz5lzkcalrgtpzp2s4ap0uu

# Anchor both checks and subsequent operations to open directories, not a path
# that could resolve to the local fallback after a mount change.
open_stash() {
  exec 9<"$mount"
  cd /proc/$$/fd/9
  verify_mount 9
}
verify_mount() {
  local mid
  mid=$(awk '$1=="mnt_id:" {print $2}' "/proc/$$/fdinfo/$1")
  awk -v id="$mid" -v target="$mount" '
    $1==id && $4=="/" && $5==target {
      split($0,a," - "); split(a[2],b," ");
      if (b[1]=="nfs4" && b[2]=="192.168.2.31:/volume1/newport") ok=1
    } END {exit !ok}' /proc/$$/mountinfo || { echo 'Wrong or missing Stash mount' >&2; return 1; }
}
open_stash
case ${1:-backup} in
  mount-check) exit ;;
  init)
    mkdir -m 700 cheesetown-restic-v1
    cd cheesetown-restic-v1
    mkdir -p -m 700 "$(dirname "$credentials")"
    (set -o noclobber; openssl rand -hex 32 >"$credentials")
    age -r "$recipient" -o password.age "$credentials"
    sync -d password.age
    ;;
  *) cd cheesetown-restic-v1 ;;
esac
exec 8<.
verify_mount 8
[[ $(stat -c '%a:%u' .) == "700:$(id -u)" ]]
[[ $(stat -c '%a:%u' "$credentials") == "600:$(id -u)" ]]
case ${1:-backup} in init) mkdir -m 700 repository ;; esac
exec 5<repository
verify_mount 5
export RESTIC_PASSWORD_FILE=$credentials
export RESTIC_REPOSITORY=/proc/$$/fd/5
case ${1:-backup} in
  init) restic init; exit ;;
  restic) shift; exec restic "$@" ;;
  restic-cwd) workdir=$2; shift 2; cd -- "$workdir"; restic "$@"; exit ;;
  escrow) cmp -s "$credentials" <(age -d -i "$HOME/.config/sops/age/keys.txt" password.age); exit ;;
  backup|pilot) ;;
  *) exit 2 ;;
esac
restic cat config >/dev/null
mkdir -p -m 700 "$state"
exec 7>"$state/lock"
flock -n 7
cd "$project"
rcon() { timeout 30 docker compose exec -T minecraft rcon-cli "$@"; }
mc=$(docker compose ps -q minecraft)
[[ -n $mc && $(docker inspect -f '{{.State.Health.Status}}' "$mc") == healthy ]]
stage=$(mktemp -d "$state/capture.XXXXXXXX")
mkdir "$stage"/{fabric-data,provisioned-mods,project}
rsync -aH -- ./ "$stage/project/"
rsync -aH -- "$base/provisioned-mods/" "$stage/provisioned-mods/"
resume=0
recover() {
  if ((resume)); then
    docker start "$mc" >/dev/null || return
    for ((i=0;i<90;i++)); do
      if [[ $(docker inspect -f '{{.State.Health.Status}}' "$mc") == healthy ]] && rcon save-on; then
        resume=0
        return
      fi
      sleep 2
    done
    echo 'Minecraft failed to return healthy with saving enabled' >&2
    return 1
  fi
}
trap 'rc=$?; trap - EXIT; recover || rc=1; exit "$rc"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
rcon 'say Backup maintenance in 30 seconds: a brief restart will save and capture the world.'
sleep 30
# During migration, do not overlap the legacy writer's save-off/save-on window.
if [[ -f $base/backups/.mc-backup-lock ]]; then
  exec 6<"$base/backups/.mc-backup-lock"
  flock -n 6
fi
rcon save-on
rcon 'save-all flush'
resume=1
printf 'Capture stop: %s\n' "$(date -Is)"
docker compose stop minecraft
[[ $(docker inspect -f '{{.State.Status}}:{{.State.ExitCode}}' "$mc") == exited:0 ]]
# Exact verified tile file types in the three currently configured map trees.
filters=()
for map in world world_the_end world_the_nether; do
  for ext in png prbm.gz; do
    filters+=("--exclude=/bluemap/web/maps/$map/tiles/**/*.$ext")
  done
done
timeout 120 rsync -aH "${filters[@]}" -- "$base/fabric-data/" "$stage/fabric-data/"
recover
printf 'Minecraft healthy: %s\n' "$(date -Is)"
if [[ -f /proc/$$/fd/6 ]]; then flock -u 6; fi
verify_mount 5
printf 'Capture directory: %s\n' "$stage"
(cd "$stage"; restic backup --json --group-by host,tags --host newport --tag cheesetown fabric-data provisioned-mods project) >"$state/$(basename "$stage").jsonl"
jq -e 'select(.message_type=="summary")' "$state/$(basename "$stage").jsonl"
# The migration pilot, restores, failed captures and all repository history are kept.
if [[ ${1:-backup} == backup ]]; then rm -rf -- "$stage"; fi

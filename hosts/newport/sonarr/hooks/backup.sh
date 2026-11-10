#!/bin/sh
set -eu
fail() { echo 'Sonarr native backup failed; refusing an unprotected update.' >&2; exit 75; }
command=$(curl --silent --show-error --fail --max-time 15 --config /config/.infra/api.curl -H 'Content-Type: application/json' -d '{"name":"Backup"}' http://localhost:8989/api/v3/command) || fail
id=$(printf '%s' "$command" | jq -er '.id') || fail
deadline=$(($(date +%s) + 120))
while [ "$(date +%s)" -lt "$deadline" ]; do
  result=$(curl --silent --show-error --fail --max-time 5 --config /config/.infra/api.curl "http://localhost:8989/api/v3/command/$id") || fail
  status=$(printf '%s' "$result" | jq -er '.status') || fail
  case "$status" in
    completed) echo 'Sonarr native backup completed.'; exit 0 ;;
    failed|aborted) fail ;;
  esac
  sleep 2
done
fail

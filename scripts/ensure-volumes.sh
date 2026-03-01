#!/usr/bin/env bash
set -euo pipefail

# Ensure bind-mount volume directories exist for a given host compose file.
#
# Usage:
#   ./scripts/ensure-volumes.sh <host>
#   ./scripts/ensure-volumes.sh newport
#
# Notes:
# - Parses compose YAML directly (PyYAML) so it does NOT require env files to exist.
# - Creates directories only for bind mounts under ./volumes/... paths.

HOST=${1:-}
if [[ -z "$HOST" ]]; then
  echo "usage: $0 <host>"
  exit 1
fi

BASE="hosts/${HOST}"
COMPOSE_FILE="${BASE}/compose.yml"

if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "compose file not found: $COMPOSE_FILE"
  exit 1
fi

mkdir -p "${BASE}/volumes"

python3 - "$COMPOSE_FILE" "$BASE" <<'PY'
import os
import sys
import yaml

compose_file = sys.argv[1]
base = sys.argv[2]

with open(compose_file, "r", encoding="utf-8") as f:
    doc = yaml.safe_load(f) or {}

services = doc.get("services", {}) or {}
wanted = set()

for _, svc in services.items():
    for vol in (svc.get("volumes") or []):
        src = None

        if isinstance(vol, str):
            # host:container[:mode]
            parts = vol.split(":")
            if len(parts) >= 2:
                src = parts[0]
        elif isinstance(vol, dict):
            # long syntax: type/source/target
            src = vol.get("source")
            typ = vol.get("type")
            # only bind-like sources under volumes path
            if typ not in (None, "bind"):
                continue

        if not src:
            continue

        if src.startswith("./volumes/") or src.startswith("volumes/"):
            rel = src[2:] if src.startswith("./") else src
            target = os.path.normpath(os.path.join(base, rel))
            wanted.add(target)

for path in sorted(wanted):
    os.makedirs(path, exist_ok=True)
    print(f"ensured {path}")

print(f"done: ensured {len(wanted)} volume dir(s)")
PY

#!/usr/bin/env bash
set -euo pipefail

# Usage: ./scripts/render-secrets.sh <host>
# Example: ./scripts/render-secrets.sh newport

HOST=${1:-}
if [[ -z "$HOST" ]]; then
  echo "usage: $0 <host>"
  exit 1
fi

BASE="hosts/${HOST}"
SECRETS_DIR="${BASE}/secrets"
OUT_DIR="${BASE}/.runtime-secrets"

mkdir -p "$OUT_DIR"

shopt -s nullglob
for f in "$SECRETS_DIR"/*.enc.yaml "$SECRETS_DIR"/*.enc.yml; do
  name=$(basename "$f")
  base="${name%.enc.yaml}"
  base="${base%.enc.yml}"

  if [[ "$base" == *.env ]]; then
    out="$OUT_DIR/$base"
  else
    out="$OUT_DIR/$base.env"
  fi

  # Decrypt YAML secrets and render them as dotenv KEY=VALUE output.
  sops -d --output-type dotenv "$f" > "$out"
  chmod 600 "$out"
  echo "rendered $out"
done

echo "done. compose can load env_file(s) from $OUT_DIR"

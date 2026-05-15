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

shopt -s globstar nullglob
for f in "$BASE"/**/secrets/*.enc.yaml "$BASE"/**/secrets/*.enc.yml; do
  secrets_dir=$(dirname "$f")
  base_dir=$(dirname "$secrets_dir")
  out_dir="${base_dir}/.runtime-secrets"

  mkdir -p "$out_dir"

  name=$(basename "$f")
  base="${name%.enc.yaml}"
  base="${base%.enc.yml}"

  if [[ "$base" == *.env ]]; then
    out="$out_dir/$base"
  else
    out="$out_dir/$base.env"
  fi

  # Decrypt YAML secrets and render them as dotenv KEY=VALUE output.
  sops -d --output-type dotenv "$f" > "$out"
  chmod 600 "$out"
  echo "rendered $out"
done

echo "done. compose can load env_file(s) from sibling .runtime-secrets directories"

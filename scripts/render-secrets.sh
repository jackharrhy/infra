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

  if [[ "$base" == *.htpasswd ]]; then
    out="$out_dir/$base"
  elif [[ "$base" == *.env ]]; then
    out="$out_dir/$base"
  else
    out="$out_dir/$base.env"
  fi

  if [[ "$base" == *.htpasswd ]]; then
    # Traefik expects htpasswd's user:hash format rather than dotenv output.
    sops -d --output-type dotenv "$f" | sed 's/=/:/' > "$out"
  else
    # Docker Compose interpolates $VAR in env_file values. Escape literal dollar
    # signs from SOPS output so containers receive the original secret value.
    sops -d --output-type dotenv "$f" | sed 's/\$/$$/g' > "$out"
  fi
  chmod 600 "$out"
  echo "rendered $out"
done

echo "done. compose can load env_file(s) from sibling .runtime-secrets directories"

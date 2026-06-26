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
    output_type=dotenv
  elif [[ "$base" == *.yml || "$base" == *.yaml ]]; then
    out="$out_dir/$base"
    output_type=yaml
  else
    out="$out_dir/$base.env"
    output_type=dotenv
  fi

  # Most secrets are rendered as dotenv KEY=VALUE files for Compose env_file.
  # Files named *.yml.enc.yaml / *.yaml.enc.yaml are rendered back to YAML for
  # apps that need structured secret config, such as Authelia's users database.
  sops -d --output-type "$output_type" "$f" > "$out"
  chmod 600 "$out"
  echo "rendered $out"
done

echo "done. compose can load env_file(s) from sibling .runtime-secrets directories"

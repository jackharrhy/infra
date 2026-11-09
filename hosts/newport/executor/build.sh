#!/usr/bin/env bash
# A clean pinned checkout plus the reviewed patch produces the local deployment image.
set -euo pipefail
infra_root=$(cd -- "$(dirname -- "$0")/../../.." && pwd)
mkdir -p "$infra_root/tmp"
source_dir=$(mktemp -d "$infra_root/tmp/executor-build.XXXXXX")
trap 'rm -rf -- "$source_dir"' EXIT
git clone --quiet --depth 1 --branch executor@2.0.0-beta.37 \
  https://github.com/UsefulSoftwareCo/executor.git "$source_dir"
test "$(git -C "$source_dir" rev-parse HEAD)" = b31108468cf5e3857f00788eac809480a7371466
git -C "$source_dir" apply "$infra_root/hosts/newport/executor/sso-only.patch"
docker build --tag local/executor:2.0.0-beta.37-auth-only.2 \
  --file "$infra_root/hosts/newport/executor/Dockerfile" "$source_dir"

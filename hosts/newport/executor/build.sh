#!/usr/bin/env bash
# A clean pinned checkout plus the reviewed patch produces the local deployment image.
set -euo pipefail
infra_root=$(cd -- "$(dirname -- "$0")/../../.." && pwd)
mkdir -p "$infra_root/tmp"
source_dir=$(mktemp -d "$infra_root/tmp/executor-build.XXXXXX")
trap 'rm -rf -- "$source_dir"' EXIT
git clone --quiet --depth 1 --branch executor@2.0.0-beta.41 \
  https://github.com/UsefulSoftwareCo/executor.git "$source_dir"
test "$(git -C "$source_dir" rev-parse HEAD)" = 6b15de8db0d96e5662c225328a1ff8177cc4db8f
git -C "$source_dir" apply "$infra_root/hosts/newport/executor/sso-only.patch"
docker build --tag local/executor:2.0.0-beta.41-auth-only.1 \
  --label org.opencontainers.image.revision=6b15de8db0d96e5662c225328a1ff8177cc4db8f \
  --file "$infra_root/hosts/newport/executor/Dockerfile" "$source_dir"

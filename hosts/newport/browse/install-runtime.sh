#!/usr/bin/env bash
# Install a verified, immutable release without upstream's global agent-config installer.
set -euo pipefail
umask 077
runtime=/mnt/terrabud/tools/browse-runtime-v0.0.16
mkdir -p "$runtime"
curl -fsSL https://github.com/anomalyco/browse/releases/download/v0.0.16/opencode-browse-0.0.16.tgz \
  -o "$runtime/package.tgz"
printf '62defcc43ada622069b0e54a8c1b27ecbe586701d24ddfc0b9151801bed12ab8  %s\n' \
  "$runtime/package.tgz" | sha256sum -c -
npm install --prefix "$runtime" --ignore-scripts --no-audit --no-fund "$runtime/package.tgz"
root=$(cd -- "$(dirname -- "$0")" && pwd)
install -m 755 "$root/browse" "$HOME/.local/bin/browse"
# Review/configure remote listening and firewall before enabling the service;
# no upstream installer, automatic pairing, agent configuration or firewall writes here.
"$HOME/.local/bin/browse" --version

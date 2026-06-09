#!/usr/bin/env bash
set -euo pipefail

# Idempotently add local preview hostnames to /etc/hosts on macOS.
# Usage:
#   chmod +x install-mac-hosts.sh
#   ./install-mac-hosts.sh
#
# Optional override:
#   PREVIEW_IP=100.x.y.z ./install-mac-hosts.sh

PREVIEW_IP="${PREVIEW_IP:-100.123.66.70}"
HOSTS=(
  dwellsmart.newport
  siliconharbour.newport
  silicon.newport
  plow.newport
  where-the-plow.newport
  preview.newport
)

START_MARKER="# >>> nano preview-router hosts >>>"
END_MARKER="# <<< nano preview-router hosts <<<"
TMP_FILE="$(mktemp)"
trap 'rm -f "$TMP_FILE"' EXIT

if [[ "$(uname -s)" != "Darwin" && "${FORCE:-0}" != "1" ]]; then
  echo "This script is intended for macOS. Set FORCE=1 to run anyway." >&2
  exit 1
fi

echo "Adding preview hosts for ${PREVIEW_IP}: ${HOSTS[*]}"

# Remove previous managed block, if present.
sudo awk -v start="$START_MARKER" -v end="$END_MARKER" '
  $0 == start { skip = 1; next }
  $0 == end { skip = 0; next }
  skip != 1 { print }
' /etc/hosts > "$TMP_FILE"

{
  echo "$START_MARKER"
  printf '%s' "$PREVIEW_IP"
  for host in "${HOSTS[@]}"; do
    printf ' %s' "$host"
  done
  printf '\n'
  echo "$END_MARKER"
} >> "$TMP_FILE"

sudo cp "$TMP_FILE" /etc/hosts

# Flush macOS DNS cache. These commands are safe if one of them is unavailable.
sudo dscacheutil -flushcache 2>/dev/null || true
sudo killall -HUP mDNSResponder 2>/dev/null || true

echo "Done. Try:"
echo "  http://dwellsmart.newport:18088/"
echo "  http://siliconharbour.newport:18088/"
echo "  http://plow.newport:18088/"
echo "  https://newport.hedgehog-python.ts.net:8443/  # DwellSmart"
echo "  https://newport.hedgehog-python.ts.net:8444/  # Silicon Harbour"
echo "  https://newport.hedgehog-python.ts.net:8445/  # where-the-plow"
echo
echo "Note: /etc/hosts cannot map ports, and custom HTTPS names like"
echo "https://dwellsmart.newport:8443 will not match Tailscale's TLS cert."
echo "Use the custom hostnames over Caddy HTTP :18088, or the Tailscale HTTPS name/ports."

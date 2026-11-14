#!/usr/bin/env bash
# Optional authenticated private MCP adapter; never installs a public endpoint.
set -euo pipefail
umask 077
runtime=/mnt/terrabud/tools/browse-supergateway-v4.2.2
mkdir -p "$runtime"
curl -fsSL https://registry.npmjs.org/supergateway/-/supergateway-4.2.2.tgz -o "$runtime/package.tgz"
python3 - <<'PY'
import base64
import hashlib
from pathlib import Path
p = Path('/mnt/terrabud/tools/browse-supergateway-v4.2.2/package.tgz')
assert base64.b64encode(hashlib.sha512(p.read_bytes()).digest()).decode() == (
    'gJLr9Fsz8MsrjdXN1iDppEucMVNctJfkkotApCCbzE01UXOrUxXn0F77dKjmuI76FLZ6UkbgeFK588PYHl/FsQ=='
), 'Supergateway integrity mismatch'
PY
npm install --prefix "$runtime" --ignore-scripts --no-audit --no-fund "$runtime/package.tgz"
python3 - <<'PY'
import os
import secrets
from pathlib import Path
root = Path.home() / '.local/share/browse'
root.mkdir(mode=0o700, parents=True, exist_ok=True)
path = root / 'mcp-api-key'
# Never rotate an already provisioned account's key implicitly.
if not path.exists():
    with path.open('x') as stream:
        os.fchmod(stream.fileno(), 0o600)
        stream.write(secrets.token_urlsafe(48) + '\n')
PY
# Enable the reviewed service/route separately, after checking local firewall/auth.

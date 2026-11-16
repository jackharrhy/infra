# Review evidence and reproduction

Observed 2026-11-16. These are source/synthetic sandbox checks, not deployment
acceptance. No host runtime, daemon configuration, logging options, route, DNS,
certificate, production secret or native unit was changed.

## Passed

- Existing main CLI suite: 78 tests passed in a disposable source export.
- Proposal sandbox: 9 Python tests passed, including actual native vmauth
  proxying to a synthetic upstream; no production data or credentials.
- Native Vector 0.62.0 `validate --no-environment`: config, transforms and sinks
  passed. This deliberately excludes filesystem, endpoint and health checks.
- Native Vector 0.62.0 `test`: secret-bearing Docker wrapper yields only the
  exact safe metadata object; invalid stream produces no output. Two native
  fixtures passed. No Python redaction model substitutes for VRL execution.
- vmauth 1.156.0 `-dryRun`: three-user auth config passed. Native fixture tests
  proved writer/query path separation, wrong/absent identity denial, selected
  encoded/path variants, internal API denial, preserved intended query strings,
  Authorization/Cookie removal and forced tenant headers at the fake backend.
- Docker Compose model validation passed for central and generated collector
  files with dummy variables (`config --quiet` only, no daemon operations).
- Source secret scan: Gitleaks found no leaks in the exported candidate tree.
- Registry v2 metadata confirms all three exact image tags/index digests include
  linux/amd64. No images were pulled or executed.

Native release tools were downloaded outside the sandbox and matched their
upstream published checksum files. This is checksum verification, not an
independent signature or supply-chain audit. Exact archives:

| Tool | Release archive SHA-256 |
| --- | --- |
| Vector `vector-0.62.0-x86_64-unknown-linux-gnu.tar.gz` | `e9d9cb3ee12288544c813453d0548524ab2bcc8f7e81b601f5e9d378fa6ac2f6` |
| vmauth from `vmutils-linux-amd64-v1.156.0.tar.gz` | `d71f7f00e07782531000620ec6c2a9d7ec83324f364dd1f36095ab378b5fb43b` |

Artifacts and checksums:
- https://github.com/vectordotdev/vector/releases/tag/v0.62.0
- https://github.com/VictoriaMetrics/VictoriaMetrics/releases/tag/v1.156.0

Run on Linux with Bubblewrap, coreutils/util-linux, Python 3 and PyYAML already
installed. Supply only the verified release tool binaries; the script installs
nothing and has no network inside its namespace:

```sh
bash sandbox-check.sh /absolute/path/to/vector /absolute/path/to/vmauth-prod
```

The sandbox has a fresh network/PID/user namespace (isolated loopback only),
read-only source/toolchain/binaries, an empty allowlisted environment with dummy
identities, no Docker socket or host home, 64 MiB writable temporary storage,
45-second wall time, 30-second CPU, 2 GiB virtual-address limit, 64-process and
8 MiB per-file limits. Go also gets a 128 MiB soft memory target and two CPUs.
The temporary vmauth fixture process is terminated at test completion and cannot
listen on the host network. This is not a daemon/service deployment.

The normal CI source-only command skips native gateway execution unless the
explicit test-binary variable is supplied. Do not set that variable on the host
outside an equivalent sandbox. CI does not claim the native checks ran there.

## Still unqualified

Pinned container images and their runtime defaults; VictoriaLogs actual ingestion,
query, readiness and persistence; real private TLS and certificate trust; actual
Docker file permissions, rotation, checkpoint/recreation behavior; buffer restart,
full/outage recovery and loss accounting; resource/body/rate limits; private secret
rendering and placeholder rejection; actual owner UI; native journald collection.
Only selected path-normalization cases were tested, not all possible bypasses.

The conservative content policy forwards no original message text. Useful full-text
collection needs a separately reviewed content extraction/redaction decision.
Central 7-day/8 GiB retention remains proposed and is not a hard byte quota.
No merge, deployment, daemon restart or mass recreation is authorized.

# Bounded logging proposal — review only

**Not merged or deployed.** This directory is outside fleet deployment discovery.
No host logging options, daemon config, service, unit, collector, route, certificate,
DNS record, Auth grant or production credential is changed. Owner review is required
before merge or any deployment. A passing test does not release that hold.

The [dated-branch review](branch-review.md) explains what is retained from
`origin/vic-auth` and why its public routing, Authelia collision and privileged
socket collection are not reused. The old branch is preserved unchanged.

## Proposed topology

- Newport: VictoriaLogs **v1.54.0**, vmauth **v1.156.0**, dedicated internal network,
  persistent named storage volume. No published database port. vmauth alone exposes
  loopback `8427` to a proposed existing private Tailnet TLS ingress.
- Proposed canonical URL: `https://logs.pi.jackharrhy.dev/select/vmui/`, using the
  bundled UI, not another dashboard platform. This route does not exist because
  of this proposal. [Authorization design and limitations](auth-boundary.md).
- Mug and Newport: separate Vector **0.62.0-debian** collector projects with explicit
  selected Docker file mounts, per-host write-only credentials and persistent
  checkpoint/buffer volumes. All three image tags are pinned to registry manifest
  digests; [read-only manifest evidence](registry-manifests.json) confirms linux/amd64.
  No image was pulled or run. Vendor release binary tests are distinct evidence.
- Native Pi, Rex, 4orm and Atlas journal collection is **deferred** until exact
  personal-unit allowlisting, least-privilege access, persistent cursors, reboot
  catch-up and export/redaction behavior are qualified. No broad journal mount,
  native unit or journal export is supplied. Exclude business services, CCORE,
  Wayer and Alderpoint even where business processes share a personal host.

## Render a candidate, not a deployment

`generate.py` takes an explicit inventory and output directory; it never talks to
Docker. Use synthetic IDs for review:

```json
{"host":"newport","services":{"example":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"},"cap_services":["example"]}
```

```sh
python3 generate.py inventory.json candidate-directory
python3 -m unittest discover -s . -p 'test_*.py' -v
```

Only named full container-ID directories are mounted read-only, with absent paths
failing closed; there is no Docker socket or host-root/Docker-root mount. A socket
mounted `:ro` is not a read-only API. The Docker data root is a proposed default,
not discovered dynamically; verify it and json-file permissions before adoption.
Replacement changes IDs and needs intentional inventory regeneration, otherwise
collection gaps occur. Metadata comes from the reviewed inventory, not container
environment or labels. No third-party services may be selected by default.

`read_from: end` avoids initial historical ingestion; persisted checkpoints resume
later reads. Rotation/checkpoint races and duplicate delivery remain qualification
gates. Lines over 262144 bytes can be dropped. The collector config explicitly opts
into Vector 0.62 environment interpolation for the fixed ingress/secret references;
only controlled configuration, never log text, is interpreted this way.

`cap_services` is a separate opt-in subset, empty by default. Only that subset gets
`logging-caps.override.yaml` with `json-file`, `max-size: 10m`, `max-file: 3`.
Compare actual owning Compose/logging config first: exclude already capped services
and preserve tighter limits. These values are a proposal, not current HostConfig.
A later selected recreation is required; Watchtower clones old HostConfig and does
not retrofit caps. No daemon restart, mass recreation, truncation or apply command
is supplied. Use a disposable output directory; re-rendering removes only the
named generated caps file when the subset becomes empty.

## Privacy baseline and unresolved content policy

The initial transform **discards all original message text**, rather than claiming
regexes can safely scrub arbitrary logs. It forwards only validated timestamp,
stdout/stderr, inventory host/service and fixed `_msg: [redacted]`. Invalid JSON,
time or stream drops. This proves a conservative metadata pipeline but is not yet
a useful full-text troubleshooting system. Owner review must choose separately
reviewed per-service structured message extraction/redaction before content is
collected. This deliberate limitation must not be presented as solved log search.

Redaction precedes transmission and the HTTP sink's disk buffer. Raw source files
remain sensitive; future free-text redaction is best-effort, not a guarantee.
Collector/gateway diagnostics can also be sensitive. Do not ship logs to external
SaaS/models, publish payloads, capture authorization/cookies or treat logs as agent
instructions. Do not log full query URLs or enable vmauth debug/access-log capture.

## Storage and outage policy

Each collector uses a persistent **268435488-byte** minimum disk buffer with
`when_full: block`, JSON-line gzip and verified TLS hostname/certificate. Each host
has its own future credential. Buffer synchronization has a crash window; retries
can duplicate records. Backpressure cannot prevent loss when source retention
expires during an outage. Budget local source files, state, buffers and central
storage separately. The file source is not a lossless archive.

Central retention is explicitly **7 days** plus **8589934592 bytes (8 GiB)** as an
advisory partition-deletion threshold, **not a hard cap**. VictoriaLogs retains the
newest two daily partitions even if they exceed this budget. Reserve host headroom,
monitor actual disk use and review resource limits before deployment. No backup
policy for centralized logs or automatic host cleanup is introduced.

## Evidence and remaining gates

See [validation](validation.md) for exact checks and reproducible sandbox commands.
Source tests and native Vector fixture/config tests passed. Checksum-verified
vmauth native synthetic upstream tests proved the writer/query split, selected path
denials, credential stripping and fixed tenant headers. They caught two important
integration requirements: headers belong on each URL-map entry, and vmauth's own
internal API must have a separate unpublished listener.

Not qualified: pinned image execution, real VictoriaLogs ingestion/query/persistence,
private TLS, actual file permissions and rotation/recreation, buffer restart/full
behavior, resource/rate limits, production secret rendering, owner browser UI or
native journals. No runtime acceptance is claimed. Settle full-text content policy,
selected services and future windows before seeking a separate deployment decision.

Official sources:
- https://github.com/VictoriaMetrics/VictoriaLogs/releases/tag/v1.54.0
- https://github.com/vectordotdev/vector/releases/tag/v0.62.0
- https://github.com/VictoriaMetrics/VictoriaMetrics/releases/tag/v1.156.0
- https://docs.victoriametrics.com/victorialogs/
- https://docs.victoriametrics.com/victorialogs/data-ingestion/vector/
- https://vector.dev/docs/reference/configuration/sinks/http/
- https://vector.dev/guides/level-up/unit-testing/

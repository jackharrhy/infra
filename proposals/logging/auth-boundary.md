# Proposed private TLS and authorization boundary

Review-only source, not an installed route or deployed authentication service.
Use the existing Newport Tailnet TLS entrypoint for the proposed
`logs.pi.jackharrhy.dev` hostname. Do not restore old Authelia, create an issuer,
change JackAuth, grant roles or expose logging publicly. `private-route.yaml.example`
is intentionally outside watched directories. Existing wildcard certificate reuse
must be verified later; this proposal creates no certificate or DNS record.

`central.compose.yaml` keeps storage on a dedicated internal Docker network with
**no published database port**. Only vmauth has a loopback port for the TLS proxy.
Loopback is a host-local trust boundary, not isolation from compromised local
processes. Do not join untrusted containers to this network. Host and Docker
administrators remain trusted.

`vmauth.yaml.example` describes distinct independently revocable `mug` and
`newport` writer identities, and a separate `query-owner` identity. A later private
renderer must reject placeholder values and produce a mode-0600 file; no credentials
or renderer/provisioning integration are created here. The central Compose file
requires an explicit private config path rather than mounting the example.

- Writers match only the whole `/insert/jsonline` path. They cannot route to UI,
  query, metrics, debug or admin endpoints.
- The owner matches only `/select/.*`, including `/select/vmui/` and query APIs,
  not `/insert/*`. Root `/` deliberately has no route. Query Basic credentials
  stay in the owner's browser, never the collectors or authored articles.
- No `unauthorized_user`, catch-all `url_prefix` or `default_url` is configured.
  Missing/invalid credentials and authenticated unmatched paths must fail closed;
  do not assume all denials return the same status code. vmauth's own internal APIs
  use a separate unpublished container-loopback listener via
  `-httpInternalListenAddr=127.0.0.1:8426`; URL maps alone do not protect them.
- The TLS proxy forwards Authorization to vmauth for authentication. Each `url_map`
  entry sets its own headers: user-level headers do not protect these routes in
  the qualified version. Empty-header removal strips Authorization and Cookie on
  the storage hop. Tenant headers are
  overwritten to 0:0. Query strings are preserved, so do not log full query URIs.
- `url_prefix` names only the backend root; the original path is appended once.
  Do not add `/insert/jsonline` again or drop source path components.

These are path permissions, **not** HTTP-method enforcement, record-level host
binding, request-query allowlisting or multitenant isolation. Host labels are
client assertions; either writer can forge host fields and send arbitrary log
content to the shared tenant. This is acceptable only for the proposed trusted
personal-host scope, not a business/hostile tenant boundary. Ingest is untrusted
content and can exhaust storage; body/rate limits and resource sizing need a later
qualification decision. No claim of strict 8 GiB isolation is made.

No-network synthetic upstream tests passed with the checksum-verified official
vmauth v1.156.0 release binary: writer POST success; writer query failure; owner
UI/query success and ingestion failure; absent/wrong credentials failure; selected
encoded/normalized paths; internal API denial; backend capture proving stripped
credentials and fixed tenant headers. This tests proxying to a fixture server,
not VictoriaLogs or TLS. The image itself, private TLS listener, hostname trust,
resource sizing and real end-to-end path still require separately authorized
isolated qualification. Source-level assertions are not runtime acceptance.

Official sources:
- https://github.com/VictoriaMetrics/VictoriaMetrics/releases/tag/v1.156.0
- https://docs.victoriametrics.com/victoriametrics/vmauth/
- https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.156.0/app/vmauth/auth_config.go
- https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.156.0/app/vmauth/main.go

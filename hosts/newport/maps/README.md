# Worldview on Newport

`https://worldview.harrhy.xyz` routes through Mug to Newport's existing Maps-named
Compose services. The old `maps.jackharrhy.dev` host is retired, not an alias.

Stores under `/mnt/terrabud/docker-data/newport/`:
- `maps_ui_celld`: UI state
- `maps_service_tea`: projects and blobs
- `maps_collaboration_tea_v2`: collaboration cells

The renamed UI lives in Harrhy's `apps/worldview`; its `tea-maps` Worker identity
and the collaboration `tea-maps-collaboration` identity remain stable. Keep the
collaboration store paired with the service's map records when moving volumes.
Compilers mount ericw-tools read only.

Render `maps-ticket.enc.yaml` and `maps-service.enc.yaml` with
`./scripts/render-secrets.sh newport`. The public OAuth callback is
`https://worldview.harrhy.xyz/auth/callback`. Service and compiler public origins
are new-host-only; do not restore an additional old-host origin.

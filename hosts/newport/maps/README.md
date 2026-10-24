# Tea Maps on Newport

`maps.jackharrhy.dev` routes through Mug to Newport's Maps services.

Stores under `/mnt/terrabud/docker-data/newport/`:
- `maps_ui_celld`: UI state
- `maps_service_tea`: projects and blobs
- `maps_collaboration_tea`: collaboration cells

Collaboration uses Tea's `tea-maps-collaboration` Worker identity. Keep the
collaboration store paired with the service's map records when moving volumes.
Compilers mount ericw-tools read only.

Render `maps-ticket.enc.yaml` and `maps-service.enc.yaml` with
`./scripts/render-secrets.sh newport`. The public OAuth callback is
`https://maps.jackharrhy.dev/auth/callback`.

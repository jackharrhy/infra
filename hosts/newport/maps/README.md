# Tea Maps on Newport

`maps.jackharrhy.dev` routes through Mug to Newport's Maps services.

Stores under `/mnt/terrabud/docker-data/newport/`:
- `maps_ui_celld`: UI state
- `maps_service_tea`: projects and blobs
- `maps_collaboration_tea`: collaboration cells

Collaboration requires `wrangler.celld-cutover.jsonc` for the existing Worker
identity and cell namespace. Compilers mount ericw-tools read only.

Render `maps-ticket.enc.yaml` and `maps-service.enc.yaml` with
`./scripts/render-secrets.sh newport`. The public OAuth callback is
`https://maps.jackharrhy.dev/auth/callback`.

The local 4orm image includes unpublished Maps and Newport Shell OAuth changes.
Its archive is `/mnt/terrabud/backup/tea-maps-2026-10-08/fourm-maps-oauth-image.tar`.

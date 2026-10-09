# Tea Maps on Newport

`maps-ui`, `maps-service`, `maps-collaboration`, `maps-compiler`, and
`maps-gower-compiler` are in `../compose.yml`. Mug routes
`maps.jackharrhy.dev` to Newport. The former Worldview hostname returns 404;
Tea Maps uses its own manifest/sidecar names and cannot import browser storage
from the old origin.

Stores under `/mnt/terrabud/docker-data/newport/`:
- `maps_ui_celld`: UI state
- `maps_service_tea`: hosted projects and blobs
- `maps_collaboration_tea`: collaboration cells
- `worldview_data`, `worldview_celld`: original stores; leave them untouched

Keep `wrangler.celld-cutover.jsonc` for collaboration: it preserves the Worker
identity and map cell namespace. Native compilers mount trusted ericw-tools
executables read only and have no public route. Roll out selected services with
`infra refresh newport --service NAME`, not a full Newport refresh.

## Secrets and image pins

Render `maps-ticket.enc.yaml` and `maps-service.enc.yaml` with
`./scripts/render-secrets.sh newport`. The ticket secret is shared by service
and collaboration; the service file holds the `tea-maps-service` and
`tea-maps-server` OAuth credentials. The public `tea-maps` client redirects to
`https://maps.jackharrhy.dev/auth/callback`.

Keep `local/4orm:tea-maps-oauth-20261008` until its Newport Shell changes are
published too. Its archive is
`/mnt/terrabud/backup/tea-maps-2026-10-08/fourm-maps-oauth-image.tar`.
UI/service images use Tea commit `c0d382522af0c1ea34a663886028d573be7e983b`;
collaboration/compilers use `17429487b2c5dc82bf59d3ce45df462d4064e39a`.

## Rollback

Frozen stores and comparison reports are in
`/mnt/terrabud/backup/tea-maps-2026-10-08/final-frozen`.
Stop the three stateful Maps containers and preserve new data first. Restore
the Worldview services from the pre-cutover infra revision, using their
original stores. Restore Mug's saved `newport-origin.yml.before-tea-maps` and
old router before allowing writes. Never copy modified Tea stores over the
original Worldview stores.

# Tea Maps on Newport

`maps-ui`, `maps-service`, `maps-collaboration`, `maps-compiler`, and
`maps-gower-compiler` in `../compose.yml` are the Tea replacement for
Worldview. The UI and collaboration Workers run on separate local Celld
instances. The hosted service and native compilers are private Node containers.
Mug routes only `maps.jackharrhy.dev` to Newport. The former Worldview hostname
has no router and returns 404; there is no redirect. Tea Maps accepts only the
new project manifest and sidecar filenames.

The UI state is under `/mnt/terrabud/docker-data/newport/maps_ui_celld`.
Hosted projects and blobs are under `maps_service_tea`, and collaboration cells
are under `maps_collaboration_tea`. Their source stores are
`worldview_data` and `worldview_celld`. Keep those source stores untouched for
rollback. The collaboration container selects
`wrangler.celld-cutover.jsonc` because that preserves the original Worker
identity and map cell namespace. The other Celld store is new.

`maps-ticket.enc.yaml` supplies one random ticket secret to the hosted service
and collaboration Worker. `maps-service.enc.yaml` holds the separate secrets
generated for 4orm's `tea-maps-service` and `tea-maps-server` clients. Render
both with `./scripts/render-secrets.sh newport` from the infra root. The public
`tea-maps` client redirects to
`https://maps.jackharrhy.dev/auth/callback`.
Fourm PR 33 registers the three Maps clients. Newport currently runs the
locally built `local/4orm:tea-maps-oauth-20261008` image, which combines that
change with Newport Shell's existing local changes. Its image archive is in
`/mnt/terrabud/backup/tea-maps-2026-10-08/fourm-maps-oauth-image.tar`; keep
the live Compose image pin until those Shell changes are published too.

The UI and service images are pinned to Tea commit
`c0d382522af0c1ea34a663886028d573be7e983b`; the unchanged collaboration
and compiler images remain pinned to
`17429487b2c5dc82bf59d3ce45df462d4064e39a`. On 2026-10-08, the final
frozen copy passed integrity checks and byte-level comparisons: 3 users,
3 projects, 7 maps, 37 resource mounts, 25 builds, and 99 blobs. All seven
collaboration snapshots matched; there were no checkpoints. Reports and the
frozen source stores are under
`/mnt/terrabud/backup/tea-maps-2026-10-08/final-frozen` on Newport. The
original Worldview stores and archived images remain for rollback. Browser
storage on the old origin is inaccessible from Tea Maps and has no importer.

For rollback, stop the three stateful Maps containers before touching their
stores. The previous Worldview Compose services are available from the parent
infra revision; its two original data directories remain untouched. Restore
the saved Mug `newport-origin.yml.before-tea-maps` if the new hostname must be
removed. Start Worldview from the previous Compose revision and restore the old
router before allowing writes. Do not copy the Tea stores back into the
original Worldview stores after they have accepted writes.

Use scoped refreshes for these services. Do not refresh all of Newport to
perform a Maps rollout. Native compiler executables are mounted read only
from the existing trusted ericw-tools installation, with no public route.

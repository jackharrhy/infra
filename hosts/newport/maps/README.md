# Tea Maps on Newport

`maps-ui`, `maps-service`, `maps-collaboration`, `maps-compiler`, and
`maps-gower-compiler` in `../compose.yml` are the Tea replacement for
Worldview. The UI and collaboration Workers run on separate local Celld
instances. The hosted service and native compilers are private Node containers.
Mug routes `maps.jackharrhy.dev` to Newport. The original
`worldview.harrhy.xyz` deployment remains separate until the final cutover.

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

The four Tea Maps images are pinned to digests published from Tea commit
`17429487b2c5dc82bf59d3ce45df462d4064e39a`. Rehearse against copies of
the two Worldview stores, and compare hosted rows, blobs, and every map cell.
For final transfer, stop writes to Worldview, take SQLite backups including its
live WAL, copy blobs and the whole Celld store, rename the copied
`worldview.db` to `maps.db`, and rerun both comparisons. Keep the original
images and frozen stores for rollback. The copied browser-local IndexedDB
cannot cross origins; retain the old hostname long enough for users to export
and import it there.

Use scoped refreshes for these services. Do not refresh all of Newport to
perform a Maps rollout. Native compiler executables are mounted read only
from the existing trusted ericw-tools installation, with no public route.

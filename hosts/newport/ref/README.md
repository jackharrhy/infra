# Tea Ref on Newport

`ref-celld` in `../compose.yml` serves `ref.jackharrhy.dev`. Its store is
`/mnt/terrabud/docker-data/newport/ref_celld_tea`; credentials render to
`../.runtime-secrets/ref.env`. Keep image digests pinned and refresh only this
service with `infra refresh newport --service ref-celld`.

Archive restore resets item revision counters; clients must reload after a
cutover. Migration archives, the original image, and its cold volume backup
are in `/mnt/terrabud/docker-data/newport/ref-migration/`. They contain private
board data and images.

For rollback, stop `ref-celld` and export any new edits. Restore the original
image (use `docker load` if its registry package is unavailable) and mount
`/mnt/terrabud/docker-data/newport/ref_celld`, then start only `ref-celld`.
The original store is a cutover snapshot and does not contain later Tea edits.

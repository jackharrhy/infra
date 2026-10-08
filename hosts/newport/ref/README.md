# Tea Ref on Newport

`ref-celld` in `../compose.yml` serves `ref.jackharrhy.dev` from the Tea
monorepo image. Its Celld store is
`/mnt/terrabud/docker-data/newport/ref_celld_tea`; the password is rendered to
`../.runtime-secrets/ref.env`. Keep the image digest pinned when changing the
runtime or application, and roll out only this service with
`infra refresh newport --service ref-celld`.

The October 2026 migration used Tea Ref's `ref-archive` version 1 export and
restore. It transferred one board, 49 items, 12 uploaded assets, and 36 cached
previews. The authenticated public archive after cutover matches the frozen
source archive for board content, layout, metadata, and asset digests. Item
revision counters are reset by archive restore; clients should reload after a
cutover. The original Celld volume is retained at
`/mnt/terrabud/docker-data/newport/ref_celld`.

Private migration material is in
`/mnt/terrabud/docker-data/newport/ref-migration/`: the frozen source archive,
post-cutover archive, original image tarball, and cold backup of the original
Celld volume. These contain board data and images; keep them private.

For rollback, stop `ref-celld`, change its image to the saved original image
and its mount to `ref_celld`, then start only `ref-celld`. That original store
is a snapshot from cutover, so export and save any new Tea Ref edits before
switching back. The archived source image can be loaded with `docker load` if
the retired registry package is unavailable.

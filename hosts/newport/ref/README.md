# Tea Ref on Newport

`ref-celld` in `../compose.yml` serves `ref.jackharrhy.dev`. Its store is
`/mnt/terrabud/docker-data/newport/ref_celld_tea`; credentials render to
`../.runtime-secrets/ref.env`. Keep image digests pinned and refresh only this
service with `infra refresh newport --service ref-celld`.

Archive restore resets item revision counters; clients must reload after a
cutover. The original `ref_celld` store and private `ref-migration` archive were
removed after cutover confirmation, so the old-image rollback is no longer
available. Back up the current `ref_celld_tea` store before replacing the image
or restoring data.

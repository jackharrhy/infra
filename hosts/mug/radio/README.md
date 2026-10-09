# Tea Radio on Mug

`radio-celld` in `../compose.yml` serves `radio.jackharrhy.dev` from Tea's
container image. Its persistent store is `../volumes/radio_celld_tea/`, and its
runtime credentials come from `../.runtime-secrets/radio-minio.env`. The store
uses a single-node Celld SQLite object database. Keep the whole mount,
including any SQLite WAL, when backing it up.

Tea's cutover configuration deliberately deploys the original `radio` Worker
and `radio-tracks` logical bucket. The default `tea-radio` configuration is for
new isolated stores and cannot read these copied rooms or audio objects. Keep
`RADIO_CELLD_DEPLOY_CONFIG=wrangler.celld-cutover.jsonc` for this production
store. Deploy a reviewed image digest with `infra refresh mug --service
radio-celld`; Watchtower does not update this stateful service.

The retired `../volumes/radio_celld/` store and the Newport migration archive
were removed after cutover confirmation. Back up the current
`../volumes/radio_celld_tea/` store before replacing the Tea image or restoring
data.

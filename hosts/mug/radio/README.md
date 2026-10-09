# Tea Radio on Mug

`radio-celld` serves `radio.jackharrhy.dev`.

- Store: `../volumes/radio_celld_tea/` (SQLite database and WAL)
- Credentials: `../.runtime-secrets/radio-minio.env`
- Deploy: `infra refresh mug --service radio-celld`

`RADIO_CELLD_DEPLOY_CONFIG=wrangler.celld-cutover.jsonc` selects the `radio`
Worker and `radio-tracks` bucket. The default `tea-radio` namespace cannot read
this store.

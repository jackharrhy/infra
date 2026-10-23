# Tea Ref on Newport

`ref-celld` serves `ref.jackharrhy.dev`.

- Store: `/mnt/terrabud/docker-data/newport/ref_celld_tea`
- Credentials: `../.runtime-secrets/ref.env`
- Image: `ghcr.io/jackharrhy/tea-ref:latest`; Watchtower updates it after Tea publishes from `main`.
- Manual refresh: `infra refresh newport --service ref-celld`

Archive restore resets item revision counters; clients must reload afterward.

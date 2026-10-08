# Tea Artbin on Newport

`artbin` in `../compose.yml` serves `artbin.jackharrhy.dev` from the Tea monorepo image. The name, Fourm client ID, OAuth callback origin, Traefik hostname, and user-facing design stay the same. The image is published as `ghcr.io/jackharrhy/tea-artbin:latest`; Watchtower can update this tag after subsequent Tea main builds.

The Tea data is under `/mnt/terrabud/docker-data/newport/artbin_tea_data`. Its `data`, `uploads`, and `tmp` directories mount at `/app/apps/artbin/data`, `/app/apps/artbin/public/uploads`, and `/app/apps/artbin/tmp/uploads`. The original directories remain under `artbin_data`; do not mount those into the Tea image. The Artbin environment secret remains `../.runtime-secrets/artbin.env`.

For the first cutover, copy the original data while it runs, then stop only `artbin` and make a final `rsync -a --delete` of each of `data`, `uploads`, and `tmp` into the Tea directories. Confirm `PRAGMA integrity_check` on the copied SQLite database, compare file counts and a checksum pass, then refresh only `artbin`. Verify the hostname, login page, folder browsing, media, and CLI API. Retain the original image tar and cold source directories for rollback.

For rollback, stop only `artbin`, use the original `ghcr.io/jackharrhy/artbin:main` image (or the saved image tar), change the three mounts back to `artbin_data` and `/app/apps/web/{data,public/uploads,tmp/uploads}`, then restart only `artbin`. Save any Tea-side writes first; the cold original copy will not contain them.

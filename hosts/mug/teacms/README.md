# Tea CMS preview on Mug

The `teacms` Compose service runs `apps/cms` from `jackharrhy/tea` and serves `andrew.jackharrhy.dev`, `luke.jackharrhy.dev`, and `teacms.jackharrhy.dev` through `traefik/dynamic/teacms.yml`. It is separate from the live `andrewsite_remix` and `andrewsite_media` services. The site manifests in the Tea CMS image set both sites to preview mode, which disables analytics and indexing.

Data is in `volumes/teacms/{andrew,luke,operator}`. Andrew was adopted from a copy of the 2026-09-24 production backup; Luke and the operator account came from the Newport preview. No site data is in Git. The initial operator login is the same as the Newport preview; its sessions were cleared before copying.

Pushes to `main` that change Tea's `apps/cms`, its shared packages, or image build inputs publish `ghcr.io/jackharrhy/tea-cms:latest` after the CMS check. The `teacms` service follows that tag. Watchtower reads Mug's existing GHCR login from `/home/jack/.docker/config.json` and updates the opted-in CMS container on its normal polling schedule. Keep that login able to read the private Tea CMS package.

After the first `:latest` image is available, switch the service and restart Watchtower once:

```sh
cd ~/infra/hosts/mug
docker compose pull teacms
docker compose up -d --no-deps --wait teacms watchtower
```

Check `/healthz` on both preview site hosts and the operator sign-in redirect at `teacms.jackharrhy.dev`. The production `andrewsite_remix` and `andrewsite_media` services must keep their existing container IDs. To roll back, set the `teacms` image to a known commit tag or digest and run `docker compose pull teacms && docker compose up -d --no-deps --wait teacms`. The pre-switch image archive is in `~/backups/teacms/teacms-image-before-tea-20261008.tar.gz`; if its registry image is unavailable, load it with `gzip -dc ~/backups/teacms/teacms-image-before-tea-20261008.tar.gz | docker load` and use `docker compose up -d --no-deps --wait teacms` without pulling.

`backup.sh` snapshots each database and copies uploads and static assets into `~/backups/teacms`, retaining about 14 days. It runs daily from `/etc/cron.d/teacms-backup`. These backups are host-local; arrange off-host replication separately. Keep the original Andrew backup archive for migration rollback.

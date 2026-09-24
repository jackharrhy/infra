# TeaCMS preview on Mug

The `teacms` Compose service serves `andrew.jackharrhy.dev`, `luke.jackharrhy.dev`, and `teacms.jackharrhy.dev` through `traefik/dynamic/teacms.yml`. It is separate from the live `andrewsite_remix` and `andrewsite_media` services. The site manifests in the TeaCMS image set both sites to preview mode, which disables analytics and indexing.

Data is in `volumes/teacms/{andrew,luke,operator}`. Andrew was adopted from a copy of the 2026-09-24 production backup; Luke and the operator account came from the Newport preview. No site data is in Git. The initial operator login is the same as the Newport preview; its sessions were cleared before copying.

After the TeaCMS check and image-publish jobs succeed, update only this service:

```sh
cd ~/infra/hosts/mug
docker compose pull teacms
docker compose up -d --no-deps --wait teacms
```

`backup.sh` snapshots each database and copies uploads and static assets into `~/backups/teacms`, retaining about 14 days. It runs daily from `/etc/cron.d/teacms-backup`. These backups are host-local; arrange off-host replication separately. Keep the original Andrew backup archive for migration rollback.

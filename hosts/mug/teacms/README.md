# Tea CMS preview on Mug

`teacms` serves `andrew.jackharrhy.dev`, `luke.jackharrhy.dev`, and the operator
UI at `teacms.jackharrhy.dev`. The sites run in preview mode (no analytics or
indexing), separately from live `andrewsite_remix` and `andrewsite_media`.

Data: `~/infra/hosts/mug/volumes/teacms/{andrew,luke,operator}`.

The service follows `ghcr.io/jackharrhy/tea-cms:latest` through Watchtower.
Mug's `~/.docker/config.json` must retain access to the private package.
Deploy with `infra refresh mug --service teacms`.

`/etc/cron.d/teacms-backup` runs `backup.sh` daily, writing database snapshots,
uploads, and static assets to `~/backups/teacms` with about 14 days' retention.

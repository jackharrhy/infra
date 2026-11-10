# Jellyfin

Runs in the Newport Compose stack at https://jellyfin.rotund.org. Mug terminates
TLS and forwards to Newport's Docker-discovered route. Port 8096 is loopback-only;
Jellyfin handles authentication directly so TV/mobile clients work normally.

## Storage and access

Only these NAS media directories are mounted, read-only:

- `/mnt/stash/media/library/movies` → `/data/library/movies`
- `/mnt/stash/media/library/tv` → `/data/library/tv`
- `/mnt/stash/media/library/documentaries` → `/data/library/documentaries`

Personal recordings/projects/clips, music, downloads and maintenance archives are
not mounted. There are no legacy path aliases. The server runs as UID/GID 1000
with supplementary media GID 65536. Stash and Newport both have this media group.
The documentary library currently contains a TV miniseries, so it uses TV metadata.

Database/configuration and cache/transcodes live on Newport under
`/mnt/terrabud/docker-data/newport/jellyfin/{config,cache}`. Only completed native
backup archives go to `/mnt/stash/newport/jellyfin-backups`, mounted at
`/config/data/backups`. NAS mounts are the host's existing fstab automounts; bind
sources use `create_host_path: false` rather than creating empty local libraries.

## Operations

Use the existing fleet CLI, not a separate service wrapper:

```sh
infra refresh newport --service jellyfin
```

NVIDIA NVENC uses Newport's Quadro P2000. AV1 hardware encoding is disabled;
unsupported inputs may require software decoding. Libraries do not save metadata,
subtitles or trickplay alongside the read-only media. NFS changes are picked up
by Jellyfin's scheduled library scans rather than inotify.

The official `jellyfin/jellyfin:latest` stable image is Watchtower-enabled. Its
pre-check hook takes a native online backup when the last successful backup is
at least a day old; its pre-update hook always takes one. Backups include the
database, metadata and subtitles, not trickplay. A failed pre-update backup
returns 75 and skips that update. This uses the existing Watchtower scheduler,
not another host service or cron job. No automatic archive deletion is configured.

The initial administrator is `jack`. Credentials and the maintenance API key are
SOPS-encrypted in `../secrets/jellyfin.enc.yaml`; the login is also saved in the
Hermes credential vault. The hook's local curl configuration is mode 0600 at
`config/.infra/backup.curl`, populated from that encrypted API key. Never log or
commit its plaintext. After a full host restore, recreate that curl configuration
before enabling automatic updates.

Restore native archives through Dashboard → Backups or the documented Jellyfin
`--restore-archive` option. Keep the current installation data before restoring;
database migrations are not safely reversed by simply downgrading the image.
The old NAS Jellyfin container is intentionally retired/stopped, not this server.

# Radarr movie watchlist

Movie automation in the Newport Compose stack. Public `https://radarr.rotund.org`
uses the same owner-only central ForwardAuth boundary as the other media admin
apps. Direct `127.0.0.1:7878` is loopback-only; no Tailnet bypass is published.
Native web authentication is external behind that boundary; API credentials remain
in `../secrets/radarr.enc.yaml`, proxy credentials in `radarr-auth.enc.yaml`.
Do not print them.

Configuration/SQLite live on Newport. Movies and download payloads live on Stash.
The shared `/data` mount supports hardlinks; tmpfs masks deny the application
access to personal files, maintenance archives, TV, documentaries, music and
unrelated download folders. No existing movie library was bulk-registered.

## Acquisition

Prowlarr supplies compatible movie indexers through its native full-sync app
connection. Radarr's built-in RSS task checks every 30 minutes; no agent cron or
extra watcher is needed. qBittorrent uses private service DNS and category
`movies`, with the existing global transfer/concurrency limits unchanged.
Completed download handling is enabled; imported files hardlink into
`/data/library/movies`, and the native Jellyfin connector requests library updates.
A future release is still pending until it actually downloads and imports.

The profile permits only WEB-DL, WEBRip and Blu-ray at 720p/1080p, ordered to
prefer 1080p. CAM, unknown, screeners, remux and 2160p are excluded. English is
selected, upgrades/renaming are off, and size bounds limit oversized files.
Minimum availability is `inCinemas`: quality rules, not a guessed digital date,
control admission once a proper release appears. The requested documentary was
resolved through native metadata to its exact title/year and stable provider IDs.
Current CAM candidates were explicitly rejected by Radarr's own decision engine.

The already queued Primetime request initially uses its separate bounded importer;
Radarr must not grab it again or interfere with unrelated TV downloads. Registering
more films remains separate scope. The rotund.org portal is a permission-filtered
directory, not an alternative authorization gate.

## Backups and verification

`hooks/backup.sh` runs the native Backup command before Watchtower updates, with
an internal deadline and failure exit75. Archives go to
`/mnt/stash/newport/radarr-backups`; credentials and config backups are private.
The first archive passed ZIP CRC and database integrity checks.

Setup checks included actual Forms login, unauthenticated API401, closed Tailnet
port, the movie's persisted monitored record, exact quality selection, native
CAM rejection, private downloader/Jellyfin connector tests, an actual cross-path
hardlink probe, app-user privacy-mask denial and clean native health.

Source test:

    uv run python -m unittest discover -s tests -p test_radarr.py

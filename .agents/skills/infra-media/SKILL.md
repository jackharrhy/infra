---
name: infra-media
description: "Use when operating the Rotund media stack."
author: Jack Harrhy, Hermes Agent
---

# Media operations

Use for Jellyfin, the Rotund directory, Navidrome, Seerr, Sonarr/Radarr,
Prowlarr, qBittorrent, Cleanuparr and their Stash library boundaries. Read
[fleet operations](../infra-host-maintenance/SKILL.md) and the relevant section of
[the media guide](../../../docs/media.md), then inspect the current manifest.
Application development and musictl replication belong in their own repositories.

## Start with the affected path

1. Identify whether the request concerns access, playback, a media request,
   acquisition, filesystem maintenance or recovery. Status inspection does not
   authorize searches, request approval, imports, account changes or deletion.
2. Verify the real NAS mount and intended media-group access before diagnosing
   missing files. Keep application databases/cache on Newport and media on Stash;
   a local empty mountpoint is not an available library.
3. Keep one runtime or NAS writer. Preserve unrelated jobs, personal media,
   native credentials and existing recovery. Use native queues/importers rather
   than another permanent watcher or agent schedule.

## Follow the complete request chain

Join exact provider IDs and requested seasons through Seerr, the native manager,
downloader hashes, imported files and Jellyfin paths. Paginate APIs and deduplicate
hashes: one season pack can cover several queue rows. Distinguish queued work,
transferring bytes, completed payloads, imports and actual playable catalog items.
A full-series percentage does not measure a season-only request.

Preserve reviewed quality, bandwidth/concurrency, monitoring and stop-only seeding
policies. More trackers do not find alternative releases or create seeders. Keep
numbering/identity exceptions held instead of filling an apparent gap with a
mislabelled episode. Selective pack and manual-import recovery require explicit
scope and the installed native API contract, not a replayed bootstrap script.

## Protect each boundary

- Jellyfin uses native accounts; the directory does not provision them. Browser
  Auth grants, native permissions and active native sessions are separate states.
- The music browser proxy's fixed native-account mapping must not become a
  multi-user allowlist. Native OpenSubsonic access still needs native credentials.
- Public admin UI and API remain gated; private automation uses existing private
  endpoints. Preserve Host/Origin/CSRF and exact proxy trust. An authentication
  error is not permission to rotate a working integration key or weaken controls.
- Cleanuparr handles scoped failed downloads, not library pruning. Completed-entry
  cleanup, partial-payload deletion and existing-library deletion are different
  permissions; entry-only removal explicitly uses `deleteFiles=false`.
- Filesystem reorganization needs an approved complete path map, identity/link
  checks, non-overwriting publication and retained originals for rewritten files.
  A review note records intent; it is not a deletion endpoint or an automatic grab.

## Finish proportionately

Use the guide's service-specific native backup/key set and stopped,
empty-destination restore procedure. Never overlay SQLite onto old WAL sidecars or
expand metadata backups to bulk media. Keep Watchtower backup gates working.

Verify only the affected contract: owner/denied login paths for access changes;
real native playback for playback changes; imported files/hardlinks and catalog
readback for acquisition; every approved file identity for filesystem changes.
Do not submit production requests as a health check. Report waiting work and
unresolved exceptions rather than converting configuration into a success claim.

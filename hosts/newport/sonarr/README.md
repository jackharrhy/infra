# Sonarr

TV/documentary inventory and future acquisition live in Newport Compose.

- Tailnet UI: http://100.123.66.70:8989
- Local API: http://127.0.0.1:8989/api/v3
- Config/database: `/mnt/terrabud/docker-data/newport/sonarr`
- Native backups: `/mnt/stash/newport/sonarr-backups`
- Native account/API key: SOPS `hosts/newport/secrets/sonarr.enc.yaml`

Retrieve the native account password locally:

    sops --decrypt --output-type json hosts/newport/secrets/sonarr.enc.yaml | jq -r '.password'

## Audit-first policy

Existing TV and documentary folders are registered by verified TVDB IDs with
matching years/IMDb IDs. Series/seasons are unmonitored; no indexer or download
client is connected. Episode renaming, empty-folder cleanup, chmod/chown and
quality upgrades are disabled. The two curated library mounts are writable for
Sonarr's root-folder validation, but no import/move/rename jobs are requested.
Movies, personal media, downloads and maintenance archives are not mounted.
Jellyfin's separate read-only boundaries are unchanged.

Library registration/rescan is not download-folder Manual Import. Some files
cannot be represented as Sonarr's single selected file per canonical episode:
bonus clips, alternate cuts, named specials and numbering differences remain
untouched on disk. Resolve unmatched main episodes before searching apparent
gaps. Specials/future episodes are not ordinary missing-episode backfill.

The temporary media site presents Sonarr's read-only API inventory and keeps the
original pruning review as an archive. Its displayed gap counts are provisional
where existing files are unmatched; it is not an acquisition trigger.

## Updates and recovery

The stable `latest` image follows normal Watchtower updates. A pre-update hook
requests Sonarr's native Backup command and waits for successful completion;
failed/unavailable backup exits 75 and blocks the update. Its private curl
header lives at `/config/.infra/api.curl`, never in Compose or browser assets.
Native scheduled backups also land in the NAS-mounted Backups directory.
Use Sonarr System → Backup to restore a native archive, not raw active SQLite
file copies. API credentials may need re-rendering after a credential rotation.

Before enabling acquisition, select actual indexers/sources and a downloader,
choose size/quality limits, and test one authorized download/import. Revisit the
mount topology for a common filesystem view and consistent paths across the
importer/downloader; the intentionally narrow audit mounts are not a verified
cross-directory hardlink acquisition setup. Keep app databases on Newport.

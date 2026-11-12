# Cleanuparr

Runs in Newport Compose using `ghcr.io/cleanuparr/cleanuparr:latest`, non-root,
with private configuration on Terrabud. The public UI at
`https://cleanuparr.rotund.org/` is fronted by a dedicated Jack Auth proxy using
exactly the existing media-admin subject restriction. UI and API paths both
require that gate; API keys and client-supplied identity headers do not bypass it.
Native Cleanuparr login remains enabled behind Jack Auth.

The direct operator/automation port stays bound only to `127.0.0.1:11011`.
Native operator credentials and API key are SOPS-encrypted in
`../secrets/cleanuparr.enc.yaml`; dedicated proxy credentials are in
`../secrets/cleanuparr-auth.enc.yaml`. Local-network and forwarded-header native
authentication bypass remain disabled. Browser callback is `/oauth2/callback`,
with PKCE/nonce and a host-only Secure/HttpOnly cookie. This admin policy is
separate from ordinary Jellyfin access.

## Policy

Sonarr v4 and Radarr v6 connect by private Compose DNS, with qBittorrent as the
verified download client. Queue Cleaner runs every five minutes:

- Metadata failure: six observations before removal/blocklist and replacement
  search, roughly half an hour depending on the first observation.
- Stalled public downloads: 48 observations, only within the first 1% completion,
  resetting strikes on progress. This allows roughly four hours without progress.
- The partial download and completed hashes existing at activation are explicitly
  ignored. Native queue inspection excludes unrelated downloads without an Arr
  content ID. Private torrents are outside the public stalled rule.
- Internet-connectivity checks guard against treating an outage as dead releases.
- Failed-import and generic error cleanup, slow-speed rules, seeding/download
  cleanup, orphan cleanup, malware blocking, proactive missing-item searches,
  custom-format upgrades and blocklist synchronization are not enabled.
- The Seeker replacement-search worker is enabled; proactive searching is off.

Dry-run observations were inspected before live activation. Actual scheduled live
metadata/stalled strikes were observed. First automatic strike-limit removal and
replacement remains a separate acceptance event; configuration/monitoring alone
must not be described as a completed automatic replacement.

Cleanuparr removes failed downloads through the Arr queue API with blocklisting.
Removing a failed unfinished torrent can discard its partial download payload;
it is not a general library cleanup tool. Do not broaden rules or turn on orphan,
import, seeding or low-speed cleanup without reviewing the scope. Existing library
files and completed/seeded content are not cleanup targets.

## Recovery and updates

`backup.py` snapshots all SQLite databases through SQLite's online backup API,
checks integrity, and retains JWT/Data Protection key files. It excludes logs and
live SQLite sidecars and atomically publishes private snapshots to
`/mnt/stash/newport/cleanuparr-backups`. No automatic backup deletion.

Watchtower remains enabled. A daily pre-check and mandatory pre-update snapshot
return exit 75 on failure, preventing an unbacked update. The helper was tested
against committed WAL data and cryptographic key files both locally and inside
the actual image. The real failure gate was exercised.

    docker exec newport-cleanuparr-1 python3 /infra/backup.py

For recovery, stop only Cleanuparr and move its current config root aside intact,
including SQLite WAL/SHM sidecars. Restore a complete snapshot into an empty config
root, not over existing databases or sidecars, with UID/GID 1000 and private modes.
Start in dry-run before enabling real changes. Retain all three databases and key
files; restoring only configuration loses authentication/strike/event continuity.
Keep the moved-aside copy until recovery is accepted.

## Prowlarr expansion

The Pirate Bay and TorrentDownload were natively tested, enabled and synced for
general TV/movie coverage. YTS was tested/enabled for movies and is not synced
into Sonarr. Existing providers remain. App-profile and effective Arr minimum
seeders are aligned to five; advertised counts are not proof of a healthy swarm.
No Cloudflare-bypass proxy or new tracker account was introduced.

Use the existing private application APIs for inspection. Do not log API keys,
authenticated download URLs or raw connection payloads. Preserve the established
bandwidth caps and quality profiles; source expansion does not authorize upgrades
or a wholesale library search.

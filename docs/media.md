# Media

Newport runs playback, requests and acquisition. Application databases/configuration
stay on Newport; curated library/download payloads stay on Stash. Use
[operations](operations.md) for single-writer maintenance, scoped refresh and
empty-destination SQLite restores. Do not interpret library inventory, a queue
entry or a successful redirect as an imported/playable result or completed login.

## Access boundaries and portal

| Host | Access |
| --- | --- |
| `jellyfin.rotund.org` | Native Jellyfin accounts; TV/mobile clients keep native login. |
| `music.rotund.org` | Jack-only Auth browser proxy mapped to the existing native account; `/rest/` uses independent native OpenSubsonic credentials. |
| `seerr.rotund.org` | Existing owner signs in with the linked Jellyfin account, not an Auth password. |
| `sonarr.rotund.org`, `radarr.rotund.org`, `prowlarr.rotund.org`, `qbittorrent.rotund.org`, `cleanuparr.rotund.org` | Separate owner-only Jack Auth proxies; both UI and public API are protected. |
| `rotund.org` | Permission-filtered service directory, not a replacement for destination authorization. |

Mug normally terminates HTTPS and relays to Newport. Jellyfin instead terminates
TLS on Newport with `home.jackharrhy.dev` DNS; its Mug fallback remains restricted.
Opt-in AdGuard LAN clients resolve the same Jellyfin host to `192.168.2.30`.
Direct application maintenance ports are loopback-only: Jellyfin 8096, Navidrome
4533, Seerr 5055, Sonarr 8989, Radarr 7878, Prowlarr 9696, qBittorrent 8087,
Cleanuparr 11011. Do not restore stale direct Tailnet UI instructions. Private
container automation uses Compose service DNS/native API credentials, not public
Auth bypasses.

Each media-admin proxy uses its own client/cookie secret, exact host
`/oauth2/callback`, code flow with S256/nonce and a one-hour host-only
Secure/HttpOnly cookie. Both the project grant and reviewed immutable subject
allowlist are required; a matching email/domain or any authenticated account is
insufficient. Native API keys and spoofed identity headers never bypass the public
gate. Provider client removal blocks new logins, not existing proxy sessions;
rotate that proxy's cookie secret and reload it for immediate cookie invalidation.
Native session/API-key revocation remains separate.

Sonarr/Prowlarr/Radarr use native External auth behind the gate; Cleanuparr keeps
native login too. qBittorrent's native bypass is only the exact Docker web bridge
gateway, not a subnet; forwarded-IP trust stays disabled. Recheck that gateway if
the network is recreated. Preserve Host validation, allowed hosts and CSRF.
Never disable these protections to repair a proxy error.

The portal is Harrhy `apps/rotund`, image `ghcr.io/jackharrhy/rotund:latest`, with
`rotund-portal.enc.yaml` and callback `/auth/callback`. Its browser cookie holds
only a signed session reference; bounded server memory holds OIDC tokens and can
be lost on restart. Anonymous pages must not leak protected links. Signed-in pages
filter by live UserInfo's exact project/org/role, not names/email/forwarded headers.
Directory roles do not provision native Jellyfin/Seerr accounts or permissions.
Navidrome and Seerr have independent directory entitlements; Gurgur remains public.
Portal logout is not global Auth logout. No business database needs restoring:
recover the matching image/source and encrypted configuration.

## Playback and requests

Verify the actual NAS mount and intended non-root/media-group access before
declaring a library missing. A stale supplementary-group membership or a path
predicate that suppresses permission errors can look like absent media. Use
`stat()` to distinguish missing from inaccessible and, where applicable, the
existing `/usr/bin/sg media` boundary rather than changing NAS ownership or ACLs.

### Jellyfin

Only `/mnt/stash/media/library/{movies,tv,documentaries}` is mounted read-only
at matching `/data/library/` paths. Music, personal recordings/projects/clips,
downloads and maintenance archives are excluded. Bind sources must already exist
(`create_host_path: false`), so a missing NAS mount cannot silently become an
empty local library. Preserve existing media-group access without broad ownership
changes. NFS content is discovered by scheduled scans, not inotify.

State/cache are `/mnt/terrabud/docker-data/newport/jellyfin/{config,cache}`.
NVENC uses the Quadro P2000; AV1 hardware encoding stays disabled and unsupported
inputs may require software decoding. Do not enable metadata/subtitle/trickplay
writes beside the read-only media.

The official stable `jellyfin/jellyfin:latest` is Watchtower-enabled. Its pre-check
backs up when the last success is at least a day old; pre-update always backs up.
Native archives contain DB, metadata and subtitles, not trickplay, and land at
`/mnt/stash/newport/jellyfin-backups` (`/config/data/backups`). Failure returns 75;
no automatic archive deletion is configured. The private mode-0600
`config/.infra/backup.curl` comes from SOPS `jellyfin.enc.yaml`; recreate it after
full-host recovery before enabling automatic updates.

Restore via Dashboard → Backups or Jellyfin's native `--restore-archive` option,
preserving the current installation first. Database migrations are not reversed
safely by simply downgrading an image. The retired NAS container is not this server.

### Navidrome

The only media mount is `/mnt/stash/media/library/music:/music:ro`; keep recovery
staging, downloads, samples, production/DJ projects and device catalogs out.
Data/bounded cache are `/mnt/terrabud/docker-data/newport/navidrome`; native DB
backups go to `/mnt/stash/newport/navidrome-backups`. Hourly scans handle NFS;
symlink following, inotify, sharing and automatic missing-file purge are disabled.

Auth browser access has a fixed existing-account mapping and a private backend
bridge trusting only its host-proxy gateway. Strip client identity headers on all
paths; `/rest/` never receives the browser mapping. Do not widen the Jack-only
allowlist until per-person native accounts, links and permissions exist and are
verified. SOPS `navidrome.enc.yaml` holds native credentials;
`navidrome-auth.enc.yaml` owns the separate client/allowlist/cookie secret.
Issuer revocation is not native music-client revocation.

The stable `navidrome/navidrome:latest` pre-update native backup must succeed or
exit 75 blocks the update. Native daily rotation keeps 14 backups; manual/pre-update
creation itself does not prune. From Newport:

```sh
docker exec newport-navidrome-1 /app/navidrome backup create --backup-dir /backups
```

Backups contain the DB, not audio/cache. Preserve SOPS/configuration with recovery;
inspect `navidrome backup restore --help` for native options and stop the service
before production restore. Keep current data first; cache is rebuildable.

Stash is the canonical listening library; Blue's offline library is independent,
not a destructive mirror. Newport processes against the Stash mount; keep bulk
transfer staging outside indexed music and off the constrained local root. Device
variants and local-only releases can be legitimate. Engine DJ's working paths,
catalogs, playlists, cues and beatgrids remain device-owned; publishing a serving
copy does not authorize moving originals, retagging or rewriting performance data.
Use musictl's own repository for replication implementation and reviewed plans.

### Seerr

Use stable `ghcr.io/seerr-team/seerr:latest`, not experimental OIDC builds.
The owner is explicitly linked to the existing Jellyfin native administrator.
New media-server-user and local-password sign-in are disabled. Auth/access-bundle
provisioning is separate work, not a configured SSO guarantee. Future ordinary
users default to REQUEST (32), without admin/auto-approve/4K/auto-request; requests
need approval, while administrators retain privileged native behavior.

Only Movies, TV and Documentaries library metadata is synced; media is not
mounted. Sonarr/Radarr use private service DNS, existing keys and approved profiles:
TV `1080p preferred - capped - no upgrades`, movies
`Movies 1080p preferred - 720p fallback`, with `/data/library/tv` and
`/data/library/movies`. No 4K backend. Approvals can initiate acquisition: do not
submit/approve production requests as health checks. Missing TMDb identifiers may
prevent availability matches. API writes need the secure XSRF-TOKEN cookie and
matching X-XSRF-TOKEN header. Stable Jellyfin Quick Connect is not proof of Auth SSO.

Config/DB/cache/logs live at `/mnt/terrabud/docker-data/newport/seerr`. The backup
helper captures all `config/db` databases consistently plus `settings.json`, not
cache/logs, into `/mnt/stash/newport/seerr-backups`. Daily pre-check and mandatory
pre-update snapshots fail closed (75), with shared [managed retention and exact-content reuse](operations.md#update-hook-backups). Restore matching
settings and `db/` together into an empty config root while stopped; retain current
WAL/SHM with the moved-aside original and preserve private runtime ownership/modes.

## Acquisition and cleanup policy

Keep current native quality profiles, transfer caps/concurrency and privacy masks;
source/indexer expansion does not authorize broad library searches, upgrades,
renaming or deletion. Prefer 1080p with bounded 720p fallback; exclude unrequested
4K/2160p, re-encoding and oversized releases. Keep waiting work fair and prevent
stalled jobs from monopolizing transfer slots. Native queues/importers are the
normal mechanism, not another agent polling daemon.

Sonarr's current Compose uses a shared `/mnt/stash/media:/data` layout, private
qBittorrent/Prowlarr connectivity and masks for personal/maintenance/movie/music
and unrelated download paths. Do not reapply obsolete audit-only mount/no-client
instructions. Existing bonus clips, alternate cuts, specials and episode-numbering
differences are not permission to move/delete files: resolve unmatched main
episodes before treating inventory gaps as backfill targets. Library registration
or rescan is not download-folder Manual Import. Preserve disabled renaming,
cleanup and upgrades unless a reviewed acquisition change explicitly needs them.

Radarr uses the same filesystem view for hardlinks, category `movies` and
`/data/library/movies`; masks exclude personal/maintenance, TV/documentaries/music
and unrelated download folders. Prowlarr full-sync supplies compatible indexers;
native RSS checks every 30 minutes. Completed-download handling imports hardlinks
and the Jellyfin connector requests scans. Preserve WEB-DL/WEBRip/Blu-ray
720p/1080p with 1080p preferred, English, bounded sizes, no upgrades/renaming;
exclude CAM/unknown/screeners/remux/2160p. `inCinemas` admission does not promise a
proper digital release. Avoid duplicate grabs for separately managed pending work;
adding more titles is separate scope. Do not bulk-register a library implicitly.

Cleanuparr handles **failed download queues**, not library or general disk cleanup.
Its configured queue cleaner cadence is five minutes: metadata failures need six
observations; public stalled downloads need 48 observations, only in the first 1%,
with strikes reset by progress. Preserve explicit ignored existing hashes,
private-torrent exclusion, the Arr content-ID boundary and connectivity checks.
Removal/blocklisting through the Arr queue API can discard partial failed payloads;
it must not target completed/seeded content or existing library files.

Seeker replacement search is enabled, proactive search is not. Failed-import,
generic-error, slow-speed, seeding/download/orphan cleanup, malware blocking,
proactive missing searches, custom-format upgrades and blocklist synchronization
stay off unless separately reviewed. Preserve Prowlarr's existing providers and
movie-only YTS scope; effective Arr/app minimum seeders are five, not proof of a
healthy swarm. Do not add a bypass proxy/tracker account or change bandwidth/quality
policy as incidental source expansion. Scheduled strikes/configuration do not prove
that an automatic strike-limit removal and successful replacement has occurred.

## Progress and entry-only cleanup

Paginate request/history APIs before claiming totals. Deduplicate download hashes;
a season pack can account for several episode queue rows. TV fulfillment is
measured against requested aired seasons/episodes, not a whole-series percentage.
Completed `queuedUP`/`stalledUP` torrents can be waiting to upload, not unfinished
downloads. Queue state, imported payload/hardlinks and the player's visible catalog
are separate evidence; do not claim a submitted search has filled the library.

Preserve the approved stop-only ratio/time policy. Check global defaults, existing
torrent overrides, indexer seed settings and synced manager values separately;
changing one default does not establish effective limits. Stopping seeding is not
removal. For separately authorized completed-entry cleanup, require imported-file
and native-history evidence, set `deleteFiles=false` explicitly, and verify retained
payload/library identities plus unfinished jobs. This is not permission to configure
future cleanup or remove anything from the listening/viewing library.

## Maintenance and recovery

Routine examples:

```sh
infra refresh newport --service jellyfin
infra refresh newport --service navidrome
infra refresh newport --service seerr
```

Inspect current use and a suitable recovery point first. Main media state is under
`/mnt/terrabud/docker-data/newport/{service}`; dedicated backups are under
`/mnt/stash/newport/{service}-backups`. Keep native credentials/API keys and
`{app}-auth.enc.yaml` proxy inputs encrypted; local curl/auth files are private,
not Compose literals, public assets or log output. Credential rotation may require
regenerating these local hook inputs.

| Service | Preservation gate / restore boundary |
| --- | --- |
| Sonarr, Radarr, Prowlarr | Native Backup command, awaited to completion before updates; failure exits 75. Restore through native System → Backup, not a live raw SQLite copy. |
| qBittorrent | Hook snapshots config, SQLite, resume metadata, job/preferences and torrent exports into its dedicated NAS directory; payloads are separate. Preserve transfer limits, stopped seeding state and current queue. |
| Cleanuparr | Online SQLite snapshots of all databases plus JWT/Data Protection key files; excludes logs/live sidecars, private atomic snapshots with managed retention. Restore all DBs/keys together into an empty config root, then start in dry-run before allowing real changes. |
| Seerr | All DBs plus settings; managed retention; recover private credentials/account/history/integrations together. |

Manual snapshots from Newport:

```sh
docker exec newport-cleanuparr-1 python3 /infra/backup.py manual
docker exec newport-seerr-1 node /infra/backup.mjs manual
```

Follow the shared stop/move-aside/empty-destination restore procedure; preserve
runtime ownership and private permissions. Cleanuparr needs all three databases
and key files for authentication/strike/event continuity, not just a configuration
DB. Failed backup hooks are a reason to repair backup access, not bypass the gate.

After an access change, check actual owner login, no-grant denial, malformed
callback rejection and anonymous/spoofed-header UI/API denial. Playback changes
need real native/browser playback as relevant; acquisition changes need the
specifically authorized download/import/hardlink outcome. Check source constraints
without treating tests as a live acceptance claim. For a playback/bootstrap change,
decode a bounded native music stream rather than treating HTTP200 as playback.
For video, distinguish actual direct browser playback from an explicitly forced
hardware-transcode check. Stop test sessions afterward; these checks are not a
requirement to replay the full media suite for an ordinary compatible patch:

```sh
uv run python -m unittest discover -s tests
```

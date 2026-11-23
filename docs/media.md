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
safely by simply downgrading an image. Inspect native archive options and ZIP CRCs;
archives can hold database table exports rather than SQLite, so a skipped SQLite
check is not an integrity check. The retired NAS container is not this server.

After a completed scan, compare actual item paths and every `MediaSources` path
before calling alternate versions missing. Extras can remain unindexed; preserve
them rather than inventing episode identities. After an approved filesystem
removal, an empty Series can survive a successful scan. Bind the exact item ID and
path, verify container-side path absence and that children stay within the approved
root before native item removal; recheck ID lookup and title search afterward.
Never delete broad search results or mistake inaccessible NAS content for absence.
For integration reads, use the installed Jellyfin `MediaBrowser` authorization
scheme; failure with a legacy token header alone does not prove key revocation.

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

For a separately approved curated/archive split, keep the roots as siblings and
retain an original-to-final identity/hash map. Stop the player and take a native
DB backup before reversible same-filesystem directory renames, then recreate it
to remount the new directory inode at its serving path. Preserve Blue/Engine
originals. Check the actual player API: default missing-file retention can leave
archived tracks in admin lists and inflate album totals. Only after proving the
NAS is present and the approved files were intentionally archived, preserve the
old catalog and consider a scoped one-time native missing-entry purge. Keep normal
`Scanner.PurgeMissing=never` protection against NAS outages. Verify visible album
counts, retained track/account IDs and decoded public audio; SQL active counts
alone are insufficient.

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

Preserve the approved six-hour/1:1 seeding cap, whichever is reached first,
with stop-only behavior and any stricter existing limits. Recheck current native
settings before changes; old bootstrap scripts may restore superseded limits.
Check global defaults, existing torrent overrides, indexer seed settings and synced
manager values separately; changing one default does not establish effective
limits. Stopping seeding is not
removal. For separately authorized completed-entry cleanup, require imported-file
and native-history evidence, set `deleteFiles=false` explicitly, and verify retained
payload/library identities plus unfinished jobs. This is not permission to configure
future cleanup or remove anything from the listening/viewing library.

## Bounded acquisition recovery

A status request stays read-only. Join native manager history and queue status to
actual downloader progress; a warning can coexist with tracked status `ok`, and
`MissingFromDisk` events can reflect a reviewed mapping change rather than an
upgrade deleting content. Verify series, season and episode monitoring separately.

For an authorized source/recovery change:

- Test a small indexer addition through the installed Prowlarr schema/native test
  before saving it. Read back categories, the actual synced minimum seeders and
  allowed quality. A catalog entry, a reachable endpoint and useful releases are
  separate evidence. Do not lower policy or add a bypass service to rescue a bad
  source. Announce trackers discover peers for one hash; indexers find alternatives.
  Keep private/passkey torrents out of public tracker trials.
- Inspect returned link schemes. A field named `magnetUrl` may contain a private
  HTTP proxy URL with an API key. Resolve only through the verified private origin
  with redirects disabled, validate the returned magnet against the selected
  well-formed infohash, and never print the proxy URL or repair malformed hashes.
- For a selective season pack, first stop at metadata with no preallocation;
  verify stopped state and zero payload bytes. Disable all file priorities, enable
  only approved missing episodes, read back the selection, then resume under normal
  caps without forced mode. Inspect `content_path` plus the actual file list:
  selectively completed files can remain under the incomplete directory.
- Verify selected-file completion, identity and size before a native import. For
  ambiguous multi-season packs, inspect the installed manual-import API: a GET may
  return existing library files rather than respect a supplied folder. Reprocess
  exact paths with explicit series/episode IDs, inspect native quality/rejections,
  then submit the separate copy-mode import. Recheck `hasFile` first to avoid
  racing completed-download handling. Verify hardlinks and Jellyfin visibility.
- Keep active useful transfers ahead of probes. A finite waiting-queue rebalance
  can interleave series via native bottom-priority moves, preserving within-series
  order. Allow cached snapshots to settle before replaying writes. Tie any bounded
  helper to the actual new search commands and a deadline, not an older cohort or
  a permanent scheduler. Retain partials; retire superseded alternatives only
  after their approved replacement is imported.

Read the installed qBittorrent schema before changing share limits. Some releases
require explicit `shareLimitAction=Stop` and `shareLimitsMode=MatchAny` as well as
ratio/time fields. Stop and limit operations settle asynchronously; verify exact
hashes and preserved payloads before retrying. A missing row can also be native
manager cleanup, not proof of payload deletion.

## Library filesystem maintenance

This is separate from service deployment and queue cleanup. Classification is
read-only until the exact change is approved; one coordinator owns NAS writes.

1. Inventory every scoped regular file with relative path, device/inode, size,
   nanosecond mtime and link count. Exclude generated `@eaDir` metadata from media
   counts without silently deleting it. Inspect downloader destinations and
   hardlinks; never rewrite a seeded/hardlinked payload in place.
2. Build a complete original-to-final map, including review/quarantine and matching
   sidecars. Verify source coverage and case-folded destination uniqueness. Keep
   language/forced/SDH suffixes, alternate cuts, extras, E00 specials and overlapping
   episode ranges. Resolve series/year/provider identity and numbering before
   comparing completeness; ambiguous names or fan edits do not justify guessed
   metadata, replacement downloads or deletion.
3. Use same-filesystem non-overwriting moves, not check-then-rename. Probe
   `renameat2(RENAME_NOREPLACE)` with disposable collision/move tests first. If the
   NFS client rejects it, use the existing trusted NAS execution context, not an
   overwriting fallback. Reject escapes/symlinks, recheck identity/size/mtime, hold
   a single-writer lock and persist/fsync intent and completion records. Scoped
   staging uses existing shared-group access, not blanket ACL/ownership changes.
4. Before SRT normalization, retain original bytes, hashes and original-inode
   backups. Decode strictly; plausible codec output alone does not resolve an
   ambiguous encoding. Normalize only text SRT encoding/line endings, preserving
   cue timing/dialogue. Do not flatten ASS/image subtitles. Review promotional
   lines within whole cues so real dialogue and translation credits survive.
   Atomically publish guarded replacements and retain authorized group/mode/time;
   never blindly replay an interrupted plan or accept an unrelated backup.
5. Independently verify every final path. Unchanged files retain identity/size/time;
   changed subtitles match planned hashes and retained originals. Archive old
   parents only after proving they contain no meaningful or expected final files.
   Keep tools, journals and recoverable clutter outside expiring scratch and the
   indexed library. Do not rehash/transcode an unchanged video collection merely
   to verify metadata-preserving moves.

For an explicitly requested large-library review, use a temporary Tailnet-only
poster/note UI with stable folder IDs, a frozen read-only metadata/file snapshot,
durable autosave/revisions and recoverable drafts. Keep API credentials server-side.
The UI records intent only: no deletion endpoint, automatic acquisition or replay
of old drafts. Interpret all notes and clarified exceptions, then approve the exact
fingerprinted file plan before changes. Display titles, feature/bonus matches and
logical bytes can mislead; verify actual content and distinguish selected logical
size from physical space reclaimed. Do not recreate a retired review tool for an
ordinary status request.

Separate DSM shares can be different Btrfs subvolumes even on one volume. Before
an approved unified-share move, probe a real cross-share `FICLONE`; do not promise
hardlinks or a no-network copy without it. Stage and journal all copies, preserve
source identity/size/time, verify destinations and ordinary-client access, then
recheck the exact source set before approved removal. A timed-out controller does
not prove the remote worker stopped: inspect its process/progress before retrying.
Audit active and stopped consumer mounts, Download Station destinations, indexing,
NFS grants and boot automounts; preserve unrelated photo/family/backup shares.
Point consumers at the canonical layout, not compatibility symlinks or bind shims.
Read indexing/task API state back; an accepted destination edit is not relocation
proof. Keep historical journals with a current path translation because cross-
subvolume moves change inode identities.

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

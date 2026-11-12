# Seerr

Stable Seerr runs in Newport Compose at https://seerr.rotund.org. Mug terminates
HTTPS and forwards the hostname to Newport's Docker-discovered route. Port 5055
is loopback-only. The official `ghcr.io/seerr-team/seerr:latest` stable tag is
Watchtower-enabled; experimental OIDC images are not used.

## Access and permissions

The initial owner is explicitly linked to the existing Jellyfin administrator's
native user ID. Sign in using that Jellyfin account, not a Jack Auth password.
New media-server user sign-in and local password sign-in are disabled. Future
account provisioning and Jack Auth access bundles are a separate integration.
No other users were imported or granted access during setup.

Default future-user permissions are REQUEST (32), without administrator,
auto-approve, 4K or auto-request permissions. Ordinary requests require approval;
Seerr administrators retain the product's privileged behavior. CSRF protection
and reverse-proxy support are enabled. API clients making writes must obtain the
secure XSRF-TOKEN cookie and send the corresponding X-XSRF-TOKEN header.

Stable Seerr also exposes Jellyfin Quick Connect. Evaluate that authenticated
linking path alongside Jellyfin SSO before considering preview OIDC. It is not
proof that Jack Auth SSO is already configured in Seerr.

## Integrations

Only the existing Movies, TV and Documentaries Jellyfin libraries are enabled.
Native Seerr library sync reads their metadata; it does not change source files.
Custom edits or items without TMDb identifiers may not match availability.

Radarr and Sonarr connect over private Compose service DNS, with their existing
API keys and existing quality profiles:

- Movies: `Movies 1080p preferred - 720p fallback`; `/data/library/movies`.
- TV: `1080p preferred - capped - no upgrades`; `/data/library/tv`.

No 4K backend is configured. Setup/tests did not submit media requests, approve
requests or initiate downloads. Approving requests later can invoke the configured
backends; do not use production requests as health checks.

## Storage and recovery

Application settings, SQLite data, cache and logs live at
`/mnt/terrabud/docker-data/newport/seerr`, owned by UID/GID 1000, mode 0700.
The settings/database contain private integration credentials and must not be
printed or committed. No media directories are mounted into Seerr.

`backup.mjs` uses Node's native SQLite online-backup API for every database under
`config/db`, verifies integrity, and copies settings.json into a private snapshot.
Completed snapshots are published under `/mnt/stash/newport/seerr-backups`.
Logs/cache are rebuildable and are not included. No automatic backup deletion.

The existing Watchtower pre-check makes a backup when the last successful one is
at least 24h old; pre-update always backs up. Both hooks return 75 on failure to
skip the update. Tests cover committed WAL contents and daily backup reuse; the
actual container's failure gate and NAS backup readback were also exercised.

Manual backup:

    docker exec newport-seerr-1 node /infra/backup.mjs

Restore only while Seerr is stopped. Move the current config root aside intact,
including database WAL/SHM sidecars, and restore settings.json and db into an empty
config root. Do not overlay a snapshot onto old database files or sidecars: an old
WAL can replace restored state. Preserve UID/GID 1000 and private modes, then restart
and verify account, request history and integrations. Retain the moved-aside copy
until recovery is accepted; never restore into a running database.

Use the existing fleet workflow for routine updates:

    infra refresh newport --service seerr

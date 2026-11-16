# Private media inventory

`refresh.py` reads existing Seerr settings in memory and performs only local GETs
against Jellyfin `/Users` and Seerr's paginated `/api/v1/user`. Existing server API
keys are broad credentials, not scoped read-only keys. Neither keys nor settings
are mounted into Auth. No account, link, invitation or role writes are performed.

Snapshots contain only service/instance/state/observedAt and accounts with immutable
nativeId, native name, disabled and administrator. Jellyfin uses native Policy
flags and the full unfiltered Users roster. Seerr has no native disabled state:
`disabled: false` means only that; administrator is ID 1 or permission bit 2.
Names are display data, never identity discovery or matching keys.

Install the service and timer into `~/.config/systemd/user/`, reload the user
manager and enable `auth-media-inventory.timer`. The user must have lingering
enabled. The service uses the primary checkout path, a 30s deadline and a private
lock; the timer runs every 60s. Run synthetic tests with
`python3 -B -m unittest discover -s hosts/newport/jack-auth/media-inventory`.

Private output is `~/.local/state/infra/media-inventory` (0700; files 0600),
readable by the Auth node UID 1000. Mount the directory read-only at
`/run/media-inventory`, not individual files: snapshots use fsync + atomic rename.
`AUTH_MEDIA_INSTANCES_FILE=/run/media-inventory/instances.json` is the only Auth
setting needed. Do not enable provisioning or native-write settings for listing.

Each provider refreshes independently. Malformed, incomplete, duplicate or oversized
rosters fail closed and retain the previous file without changing its observedAt.
Logs contain only static status and counts. Auth treats unreadable snapshots as
unavailable and observations older than five minutes as stale. Inspect the timer
and service journal for refresh failures; never retimestamp a failed observation.

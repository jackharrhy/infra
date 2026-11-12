# Navidrome

Runs in Newport's existing Compose stack at https://music.rotund.org. Mug terminates
TLS and relays to Newport's Docker-discovered route. Port 4533 is loopback-only.
Browsers sign in through Jack Auth using the dedicated OAuth2 Proxy service.
OpenSubsonic music clients retain native Navidrome authentication on `/rest/`.

## Storage

- Stash's canonical `/mnt/stash/media/library/music` is mounted at `/music`, read-only.
- Database and bounded caches live at `/mnt/terrabud/docker-data/newport/navidrome`.
- Native database backups go to `/mnt/stash/newport/navidrome-backups`.
- UID/GID 1000 and supplementary media GID 65536 match the existing NAS permissions.

Only the listening library is mounted: no recovery staging, downloads, samples,
production projects, musictl state or Engine DJ databases. Bind sources must exist;
Compose will not create substitute empty media directories. Hourly scans handle NFS
changes; inotify watching and following symlinks are disabled. Missing files are
not automatically purged. Sharing is initially disabled.

## Access

The initial administrator is `jack`. Its generated password is stored only in
`../secrets/navidrome.enc.yaml`, encrypted with the existing Infra SOPS key. Retrieve
it locally with `sops -d hosts/newport/secrets/navidrome.enc.yaml` from the Infra root.
Do not print credentials in automation logs. Use the public URL and native account
in OpenSubsonic clients; browser users do not need this separate password.

`navidrome-auth.enc.yaml` holds the dedicated OIDC client, exact reviewed Jack
subject allowlist and independent secure cookie secret. S256 and nonce checks are
enabled. Successful authorization maps that subject to the existing `jack` account,
preserving its native ID. This is deliberately Jack-only: do not widen the allowlist
until per-person native accounts, permissions and explicit identity links exist.

Traefik strips supplied identity headers on every Navidrome path. Browser routes
then authenticate before injecting the fixed account mapping; native `/rest/`
routes never receive it and still require native credentials. The backend is on
its own bridge, not the shared web network, and trusts only its host-proxy gateway
`172.30.33.1/32`. Browser logout clears the host-only proxy cookie and lands at
Jack Auth; the issuer session is managed separately. Removing an issuer grant
alone is not immediate revocation of native music-app credentials or sessions.

Acceptance covered genuine public browser callback, existing account/library,
browser audio, logout/reentry, header-spoof denial, shared-network backend isolation
and independent native-client audio decoding. No other users were provisioned.

The first administrator was created while Traefik discovery and automatic updates
were disabled for this container. Normal routing and Watchtower selection were
enabled only after login and rejection of repeat first-admin creation were tested.

## Operations

Use the existing fleet workflow:

    infra refresh newport --service navidrome

The official `navidrome/navidrome:latest` image tracks stable releases. Watchtower
is enabled. Before an update, a native online database backup must succeed;
the hook returns 75 on failure to skip that update. Native daily backup rotation
is set to 14 in this service's dedicated directory. The manual/pre-update creation
command does not itself prune backups.

Create a manual backup:

    docker exec newport-navidrome-1 /app/navidrome backup create --backup-dir /backups

Backups contain the database, not the music files or caches. Keep the SOPS login
and deployment configuration with recovery material. Inspect `navidrome backup
restore --help` for native restore options, stop this service before an actual
production restore, and preserve its existing data first. Cache can be rebuilt.

Seerr is deployed separately at https://seerr.rotund.org; see `../seerr/README.md`.
Its Jack Auth and per-person access integration remains a separate gate.

# Applications

Use [operations](operations.md) for scoped updates, SOPS and empty-destination
restore rules. Compose is the image/mount inventory, not historical rollout notes.
Public hostnames below are configuration references, not claims of fresh live tests.

## Auth and application-owned access

Jack Auth's issuer/UI is `https://auth.jackharrhy.dev`; discovery is
`https://auth.jackharrhy.dev/.well-known/openid-configuration`. Newport runs
`jack-auth-db`, `jack-auth-api` and `jack-auth-ui`; Mug splits UI/provider routing
in its canonical route file. PostgreSQL and the pinned provider are separate from
the Harrhy-published `ghcr.io/jackharrhy/auth:latest` UI image. The UI follows the
main-published tag; its existing manual-update/Watchtower exclusion is intentional.
Backend ports 18085/18086 bind Newport's tailnet address, not the public Internet.
Auth UI development is now owned by Harrhy's
[`apps/auth`](https://github.com/jackharrhy/harrhy/tree/main/apps/auth). Older
standalone checkouts and a feature branch predating that import are not proof of
current main. The old standalone deployment copy `~/repos/personal/jack-auth` on
Newport is retained recovery, not the canonical build source for the published UI.
A source
consolidation is not a provider/runtime cutover. Follow the current source owner's
provisioning/build instructions, not an invented fleet-wide Auth refresh.

Auth owns issuer resources, explicit app eligibility/grants, service-account
keys and provider/SMTP configuration. Applications own native accounts, identity
links, local roles, sessions, API/MCP credentials and content ownership. A matching
name/email/domain is not authorization to create, merge, link or grant accounts.
Use reviewed immutable subject mappings privately; do not publish actor IDs.
Machine credentials must remain app/list/scope limited. The instance-owner
bootstrap PAT and provisioning operator key never enter the UI or consumers.
The UI uses separately encrypted read-only service-account RSA keys for short-lived
API tokens. JSON credential wrappers use the renderer's top-level `json` format.
Provisioned keys have finite lifetimes; arrange explicit rotation, not assumed
automatic rotation. Preserve the runtime user's read access to private key files.

Provider sends only as `auth@jackharrhy.dev`, through SES STARTTLS on
`email-smtp.us-east-1.amazonaws.com:587`, with `secrets/smtp.enc.yaml` and the
identity in `aws/mail/index.ts`. Lists/subscriber data is independent of Auth mail.
Keep self-registration closed and explicit app grants. For delegated Artbin/Worldview
admin consent, retain exact target-app active-admin checks, PKCE/nonce, scope and
audience boundaries, CSRF/replay protection and current registration rate/body
limits. DCR clients are not automatically assigned user roles. Disabling DCR uses
`scripts/configure-dcr.py disabled` **in the Auth checkout**; it is not a general
consumer-access revocation procedure.

Removing an issuer grant/client blocks new login, not necessarily existing native
sessions/tokens. Revoke those separately and disclose incomplete revocation.
Auth cookies, consumer cookies and native-client credentials have separate lives.
Source merges, redirects and stored grants do not prove a working human login.
Do not activate held clients or privilege-bearing support login by implication.

### Provider and UI authorization-state recovery

Provider data is `/mnt/terrabud/docker-data/newport/jack-auth/postgres`.
Preserve its matching encrypted master key with consistent PostgreSQL backups and
an off-host copy. A UI ledger backup is not a full issuer backup. Provider restore
startup and automated provider retention need explicit validation/configuration;
this documentation does not assert them complete.

The UI's durable writable mount is
`/mnt/terrabud/docker-data/newport/jack-auth/ui:/data`. Keep the directory private
(mode 0700) and writable by the runtime user; SQLite files are mode 0600.
`radio-enrollment.sqlite` records enrollment/denial history; `access.sqlite`
records groups, provenance, blocks and operations. These are **Auth authorization
metadata, not Radio audio**, not disposable cache, and not consumer activation.
`RADIO_ENROLLMENT_DB_FILE` selects the ledger; `ACCESS_DB_FILE` can override the
access DB, otherwise it is derived beside the ledger.

For a routine compatible UI image update, retain the prior image and use adequate
existing recovery; no new database snapshot is required for every patch. For a
state-changing cutover or when a fresh authorization-state checkpoint is needed,
run from the Infra root on Newport:

```sh
python3 hosts/newport/jack-auth/backup-radio-ledger.py
```

The [helper](../hosts/newport/jack-auth/backup-radio-ledger.py) remains useful while
Auth owns these durable enrollment/access decisions. Its small standalone command
is shared by cron and manual maintenance: SQLite's backup API handles live WAL state
safely, unlike copying database files. It never traverses Radio audio or media.
It takes integrity-checked SQLite snapshots into the private
`/mnt/terrabud/backups/jack-auth/radio-ledger` directory. Radio uses `<run>.sqlite`,
access uses `<run>.access.sqlite`, and a completed `<run>.json` identifies the set.
`--access-source /absolute/path/to/access.sqlite` handles an overridden host path.
The `.access-required` marker makes later missing access fail closed after adoption;
preserve it. An older `absent-before-adoption` manifest is not a complete current
access-state checkpoint. Each DB is individually consistent; coordinate the Auth
runtime writer to quiesce UI writes for one logical point across both files.
Do not stop/recreate the UI underneath another owner's exclusive writer lane.

[radio-ledger-backup.cron](../hosts/newport/jack-auth/radio-ledger-backup.cron),
installed as `/etc/cron.d/jack-auth-radio-ledger`, runs daily at 04:17 host time.
There is **no automatic retention/deletion**. Restore while UI is stopped: move
current databases/sidecars aside, restore both members of the reviewed manifest
into an empty private destination, and preserve ownership/modes. Pair them with
the corresponding provider checkpoint and credential configuration. Any encrypted
lifecycle material additionally requires its matching sealed configuration/key;
the paired-DB helper does not capture that key. Do not replace newer denials with
an old empty ledger. Verify integrity and membership/block states before restart.

## Artbin support configuration

Support login is an explicit capability for the reviewed immutable Jack identity,
not a permission inherited by ordinary application administrators. Its supported
consumer is Artbin; native end-user impersonation is not an app-only capability.
The Auth config/key is sealed in
`hosts/newport/jack-auth/secrets/artbin-support.json.enc.yaml` and rendered to
`jack-auth/.runtime-secrets/artbin-support.json`, mounted read-only. Artbin receives
only the separate transport/client/origin settings from `artbin-support.enc.yaml`;
its existing resource credentials and data stay separate. Both inputs are enabled
for the reviewed Jack-only flow. Mug routes `/support/handoff`, `/support/redeem`,
`/support/session`, `/support/end` and `/support/callback` to the Auth UI.

Activation requires actor-bound Auth source and a paired UI database checkpoint
linked to the matching sealed config/key. Disabling must retain that config, key, client
and sweeper until issued tokens are inactive; deleting the config is not a safe
kill switch. The routine database backup does not capture the encryption key.

## Private vault synchronization

Use the official [headless Sync guide](https://obsidian.md/help/sync/headless) and
existing registration rather than creating another writer. Inspect desktop and
headless clients first: they must not sync the same vault concurrently. Reuse
saved authentication privately; configuration/backups can contain encryption keys
and private filenames. A successful remote listing is not completed sync.

Before the first resumed synchronization, take and verify a private backup of the
vault plus its matching headless configuration. Verify the installed Node/client
and its native SQLite module with an in-memory database before touching state;
package installation can suppress native scripts. For a stale server-side consumer,
use explicit pull-only mode when requested; mirror/remote deletion semantics are
a separate decision. Run one successful bounded sync before enabling continuous
operation. Inspect actual user-service enablement, restart behavior and private
logs; do not repair authentication by blind restart loops.

Synchronization, local build, public-content review and publication are separate
authorities. Do not put a private vault or whole attachment tree in a public image,
repo or upload merely to verify sync. Garden's current snapshot/export procedure
below supersedes older standalone-site manifest/upload commands.

## Garden: code and public writing are separate releases

The personal site is Harrhy's `apps/garden`, workspace `@harrhy/garden`.
Mug's `jackharrhy` service follows `ghcr.io/jackharrhy/garden:latest`, listens on
4322, and retains its domain aliases, low routing priority and Last.fm secret.
Its read-only content is `hosts/mug/volumes/garden-content/current` at
`/app/data/current`. Keep the private Obsidian vault off the server and outside
image build contexts. Updating the image does not publish vault content.

From the Harrhy checkout, export a public immutable snapshot:

```sh
GARDEN_COMPARE_URL=https://jackharrhy.com npm run content:export --workspace @harrhy/garden
```

Review added/changed/removed pages and referenced media. Only public pages and
their referenced assets belong in the snapshot; never upload the entire private
assets directory. From the Infra root, replace the example paths with the reviewed
snapshot and the local assets directory:

```sh
uv run scripts/publish-garden.py /absolute/path/to/snapshot --assets /absolute/path/to/vault/Assets --dry-run
uv run scripts/publish-garden.py /absolute/path/to/snapshot --assets /absolute/path/to/vault/Assets
```

The [publisher](../scripts/publish-garden.py) requires Python, rclone, SSH to Mug
and a compatible deployed image. It checks public frontmatter, listed source/media
hashes and the production diff; dry-run does not publish. After confirmation it
uploads only added/changed referenced assets to `jacks-garden:jacks-garden`,
checks hashes via `https://garden.jack.camera`, transfers an immutable release,
atomically switches `current` and restarts only `jackharrhy`. Failed health checks
switch back. Removed media is not deleted from R2. Legacy `assets:*` commands are
for separately authorized bucket maintenance, not routine content publishing.

For compatible code updates, retain the prior image and existing recovery, then
from `hosts/mug` (run any actual service-specific backup/drain hooks explicitly):

```sh
docker compose pull jackharrhy
docker compose up -d --no-deps jackharrhy
```

Retain the prior image and content release. For content rollback atomically point
`current` at the reviewed previous relative `releases/...` target, then run
`docker compose restart jackharrhy` from `hosts/mug`. Preserve the first legacy
recovery image/configuration as well; tags alone do not survive explicit pruning.

For a significant code/layout change, stage the candidate with the public snapshot
on loopback without public route labels. Check `/healthz`, public pages/feeds,
media redirects, `/home`, 404/development-route rejection and representative
browser widths, suppressing test analytics. This is a checklist, not completed
acceptance for a future image.

## Wonder private static site

`https://wonder.pi.jackharrhy.dev` is an independent Astro static site, not a p2
plugin or runtime dependency. Wonder owns source/content/build/publication in
`~/repos/personal/pi-wonder`; Infra owns Newport `wonder-site` and its explicit
private `pitailnet` route. It has no new auth layer: Tailnet reachability grants
read access. Do not put credentials or raw private research in built output.

The publisher copies only validated `dist` into
`/mnt/terrabud/websites/pi-wonder/releases/BUILD` and atomically replaces a
relative `current` symlink. Keep the prior release for rollback; a failed build
or validation must not replace current. Reject source/config/dotfiles/source maps
and symlinks in artifacts. Source and `node_modules` are never mounted in the
server. Wonder owns the publish command; scheduling is separate, not required for
site availability.

The read-only unprivileged nginx container serves only this release root, with
loopback `127.0.0.1:18810` and no automatic directory indexes. Restart p2 without
affecting the site. Static publishing needs no container restart: switch the
symlink and verify expected pages/assets over the named TLS URL; roll back the
symlink if a publication fails. Do not delete releases or volumes implicitly.

## Mug applications

| Service / public host | Persistent state and boundaries |
| --- | --- |
| `8mb` / `jackharrhy.dev/8mb/` | Harrhy `apps/8mb`; browser-only video processing, no upload endpoint/media mounts. `volumes/8mb-diagnostics` is the sole writable mount. |
| `lists` / `lists.jackharrhy.dev` | `volumes/lists_tea_data`, snapshots in `volumes/lists_tea_backups`; `/webhooks/ses` and port 8080 retained. |
| `radio-celld` / `radio.jackharrhy.dev` | `volumes/radio_celld_tea` contains the SQLite object store/WAL and state; `radio-minio.env` and `radio-central-auth.env` are runtime configuration. |
| `teacms` / `andrew.jackharrhy.dev`, `luke.jackharrhy.dev`, `teacms.jackharrhy.dev` | `volumes/teacms/{andrew,luke,operator}`; preview sites stay separate from live `andrewsite_remix`/`andrewsite_media`, without analytics/indexing. |

These services follow their existing short-name Harrhy `latest` images. Do not
reintroduce old publisher names from historical instructions. Refresh one service:

```sh
infra refresh mug --service radio-celld
```

8mb optional diagnostics default off and accept only daily aggregates, retain seven
UTC dates and expose no public read endpoint. Do not enable request/media logging.
The private diagnostics directory must exist before recreation (mode 0700,
runtime-user writable); the direct-exec umask 077 launcher preserves private
SQLite/sidecar modes. Disposable aggregates are excluded from durable backups;
that is not permission for refresh to delete their directory or other recovery data.

Lists loads SOPS `secrets/lists-tea.enc.yaml` → `.runtime-secrets/lists-tea.env`.
Preserve AWS/SQS/S3/SES/media settings and the separately list-scoped Silicon Harbour
credential. Its Bun pre-update hook creates a consistent integrity/FK-checked
SQLite snapshot and exits 75 on failure. Never refresh into an empty store or run
two worker sets concurrently. Data moves need a source drain, consistent export,
reviewed human/service mapping and no-overwrite import into a fresh destination.
Retain `volumes/lists_data` and legacy encrypted config as recovery material;
new-write rollback needs reconciliation, not a blind snapshot overwrite.

Radio's `RADIO_CELLD_DEPLOY_CONFIG=wrangler.celld-cutover.jsonc` selects the `radio`
Worker and `radio-tracks` bucket; the default `tea-radio` namespace cannot read the
same store. Preserve that existing configuration filename, `RADIO_SESSION_SECRET`,
the authoritative store and current recovery credentials/configuration. This
application store and track/audio storage are separate from the Auth enrollment/access snapshots.

Tea CMS requires private package access in Mug's `~/.docker/config.json`.
`/etc/cron.d/teacms-backup` runs the [backup script](../hosts/mug/teacms/backup.sh)
daily at 04:27 UTC on Mug, preserving both site databases/uploads/public assets
and the operator DB in `~/backups/teacms`. It retains seven newest producer-verified
daily archives (normally seven days; missed nights do not erase older recovery).
This is local recovery on the same disk, not an independent off-host backup.
Restore the whole matched set into empty destinations with the service stopped.

The prepared app-native backup bind is `volumes/teacms_backups` → `/app/backups`,
separate from `/app/data` and the old tar archive root, owned by uid 1000 with mode
0700. `create_host_path: false` requires explicit host preparation. This mount does
not enable backups: keep `TEA_BACKUP_DIR` absent until the matching image and its
backup/restore CLI have been checked. Keep the existing cron and seven good
archives through a completed native snapshot and an offline restore into a **new
private scratch directory**, using the matching image, read-only backups and no
production data mount. Never ingest/convert old tar archives or restore over live
data by implication.

The separate `andrewsite_remix` app for `andrewgossecomposer.com` mounts
`volumes/andrewsite_tea_data` at `/app/data`. Its existing OS cron calls
`hosts/mug/andrewsite/backup.sh` at 04:17 UTC, backing up SQLite plus that app's
uploads into `~/backups/andrewsite` with the same seven-snapshot retention.
These are not Docker image/whole-volume backups. In particular, the separate
read-only `andrewsite_media` mount `volumes/andrewsite_strapi_uploads` is not
covered by the current Tea DB/uploads archive; preserve that legacy media and
include it explicitly in any future application-owned recovery contract.
Keep current scheduled protections until any app-owned replacement has verified
consistent snapshots, media coverage, status and restore. Weekly/monthly tiers
are a separate retention choice, not additional cron jobs by implication.

## Newport applications

Stores below are under `/mnt/terrabud/docker-data/newport/` unless stated otherwise.

| Service / public host | State, credentials and important constraints |
| --- | --- |
| `steve` / `steve-letter-writ.ing` | `steve_tea_data`: keep `letters.sqlite` and `uploads/` together. SOPS `steve.enc.yaml` → `.runtime-secrets/steve.env`. Retain `hosts/newport/volumes/steve` as recovery; stop the current writer and reconcile newer writes before using an older store. |
| `ref-celld` / `ref.jackharrhy.dev` | `ref_celld_tea`; SOPS `ref.enc.yaml` → `.runtime-secrets/ref.env`, mounted at `/run/secrets/ref.env`. Archive restore resets revision counters: clients must reload. |
| `marky` / `md.jackharrhy.dev` | `marky_tea`, served internally on 44100; current Compose uses `marky-central-auth.env`. Preserve Auth integration and `/auth/callback`; do not restore obsolete anonymous editing or Discord-only instructions. Git PAT is only for deliberately configured Git-backed content. |
| `maps-ui`, `maps-service`, `maps-collaboration` / `worldview.harrhy.xyz` | `maps_ui_celld`, `maps_service_tea`, `maps_collaboration_tea_v2`; service records/blobs and collaboration cells must stay paired. Harrhy `apps/worldview`; retain `tea-maps`/`tea-maps-collaboration` Worker identities. |

Steve, Ref, Marky and the Worldview images follow their current short-name
Harrhy `latest` references. Examples:

```sh
infra refresh newport --service steve
infra refresh newport --service ref-celld
```

Worldview has no `maps.jackharrhy.dev` alias. Preserve the exact new-host origins
and `https://worldview.harrhy.xyz/auth/callback`. Render the `maps-ticket`,
`maps-artbin-auth` and `maps-central-auth` encrypted inputs referenced by current
mounts/env files; compiler tools remain read-only. Scope a
multi-service refresh deliberately, including only the changed UI/service/
collaboration/compiler services. Stop writes and capture paired stores for moves;
a UI redirect does not establish human/delegated Auth acceptance.

## Executor

`executor.jackharrhy.dev` serves the dashboard and `/mcp`; loopback health is
`http://127.0.0.1:4400/health`. Data is
`/mnt/terrabud/docker-data/newport/executor/data` (embedded PGlite plus keys).
No Docker socket or home-directory mount is required.

Executor is a deliberate local patched image, `local/executor:2.0.0-beta.41-auth-only.1`,
with `pull_policy: never` and Watchtower disabled. From the Infra root, after a
stopped full-data backup and maintenance checks:

```sh
hosts/newport/executor/build.sh
cd hosts/newport
docker compose up -d --no-deps executor
docker compose ps executor
docker compose logs --tail=100 executor
```

The build uses a clean pinned upstream checkout and `sso-only.patch`, not edits
in a development checkout. It performs network/build operations when deliberately
run. Stop Executor before filesystem backups; preserve permissions,
`auth-secret.key` and `encryption.key` with the database, or encrypted service
accounts cannot be recovered. Retain separate legacy CLI data; it is a different
storage format, not a replacement server database.

`BETTER_AUTH_URL` must exactly match the public HTTPS origin. Forward the entire
host, including MCP, OAuth callbacks and discovery, without another interactive
ForwardAuth gate. Saved management-app `index.ts`, `openapi.json` and `provider.ts`
also embed the installation origin: deploy corrected app source through its API
and reconnect its service account if provider identity changes.

Auth owns the dedicated confidential client and explicit eligibility;
`executor-sso.enc.yaml` renders `executor-sso.env`. The consumer owns Compose,
`SSO_DISCOVERY_URL`, `SSO_ALLOWED_DOMAINS`, native accounts/org roles/sessions and
MCP/PAT access. Use code flow, `client_secret_post`, S256/state/nonce and
`openid email profile`, without refresh/offline/delegated-role scopes. An allowed
domain alone never authorizes eligibility or owner/admin promotion. New-user
verified-domain checks are not a claim about every existing-member request.

For deliberate account adoption, link while signed into the existing native
owner, verify fresh SSO reaches the same owner/org/app without duplicates, then
enable `SSO_ONLY=true`. Do not merge accounts by email or edit identity rows to
make linking pass. Final mode rejects native password/setup registration and
fails closed on missing SSO config; discovery failure must not restore passwords.
Rollback uses the previous image/config and the compatible same data, after backup.
Local logout does not invoke provider logout. Issuer grant removal is not native
session/token revocation. For auth changes verify affected negative cases and the
real MCP consent/token/resource flow; old partial checks are not a fresh pass.

Optional app-host pages need `EXECUTOR_APP_UI_BASE_URL`, wildcard DNS and a
certificate for `*.executor-apps.jackharrhy.dev`; `*.jackharrhy.dev` does not cover
that extra label. `EXECUTOR_OAUTH_CLIENT_METADATA_URL` is optional, not assumed
configured. Private fetch is off upstream by default; this personal instance
explicitly enables `EXECUTOR_APPS_ALLOW_PRIVATE_FETCH=true` for authenticated
application integrations. This grants **all instance authored apps** private-network
egress, not just Browse. It does not make the publicly routed Executor dashboard
Tailnet-only, remove SSO, or change native grants. The deployed beta41 supports no
per-app private-fetch exception; do not confuse host-side import URL allowlists
with authored-app workerd egress. Source/fork reconciliation is separate from the
pinned runtime image; no source rebase implies deployment.

## Browse desktop browser pilot

The pinned upstream relay is Anomaly Browse **0.0.16** (source tag commit
`506de3e7bad481c7db5dca786b6e333751e15877`). The verified release package is installed
outside Git at `/mnt/terrabud/tools/browse-runtime-v0.0.16`; the launcher is
`~/.local/bin/browse`, managed by user `browse-relay.service`. The installer helper
in [hosts/newport/browse](../hosts/newport/browse/) verifies the fixed release
checksum and skips package scripts; it does not run upstream's global installer,
configure other agents or pair a browser. Relay auto-update/checks are disabled in
the launcher/service for this pinned pilot. Review new versions deliberately.

### Desktop extension and transport

Official [Chrome Web Store extension](https://chromewebstore.google.com/detail/mfnicocicmmlkpjnaffgihfjhdgjkdjg)
updates independently through the browser. For an exactly matched manual build,
use the [0.0.16 release ZIP](https://github.com/anomalyco/browse/releases/download/v0.0.16/browse-extension-0.0.16.zip)
and Load unpacked after checking its published checksum. Do not disable pairing
or widen extension Origin allowlists to paper over a version mismatch.

On the desktop with Tailscale enabled, open extension Options → advanced:

- **Relay address:** `100.123.66.70:19988` (bare Tailnet IP/port, not an HTTPS URL).
  Do **not** use a `.dev` hostname for this plain-WS endpoint: Chromium's `.dev`
  HSTS preload upgrades ws to wss and produces `ERR_SSL_PROTOCOL_ERROR` against
  the native non-TLS relay. Do not clear/disable browser security to work around it.
- On Newport, run `~/.local/bin/browse pair` in the owner's private terminal; enter
  its one-use ten-minute code in **Pairing code**, then **Connect**. Never paste
  pairing codes, relay tokens or adapter keys into chats or Git.
- Explicitly lend a non-sensitive test tab with the toolbar button. Agents must
  not inspect existing private/authenticated tabs before the owner lends them.
  The owner can take a tab back at any time; pairing alone is not consent to browse.

This extension version hardcodes **ws**, not wss, even if a wss scheme is typed.
Traffic encryption is provided by Tailscale; an HTTPS reverse proxy is not its
native relay endpoint. The separate `https://browse.pi.jackharrhy.dev/mcp` adapter
below uses real TLS and is unaffected. A WebSocket 101 probe proves transport,
not pairing; verify the extension actually reports connected, and regenerate an
expired pairing code only after correcting its address. Supported relay binding is only loopback or `0.0.0.0`.
Remote mode uses the latter with a specific Tailnet allow followed by non-Tailnet
firewall denial; verify these rules **before** starting remote mode:

```sh
sudo ufw allow in on tailscale0 to 100.123.66.70 port 19988 proto tcp comment 'Browse Tailnet extension pilot'
sudo ufw deny in to any port 19988 proto tcp comment 'Browse deny non-Tailnet ingress'
# This command prints a short-lived code: run privately, never in shared logs.
~/.local/bin/browse set hostname 0.0.0.0
```

The relay rejects remote HTTP/API and CDP requests; only the extension WebSocket
is available remotely, with the published-extension Origin check and upstream
ECDH/HMAC pairing. Local API/CDP still require the private relay token at
`~/.local/share/browse/relay-token` (0600). Do not reverse-proxy its whole HTTP API
through a trusted loopback connection, which would defeat the peer check. No
Funnel/public forwarding is used. Both the relay and execution realm trust the
Unix account; this is not a sandbox against other same-UID processes.

### Authenticated MCP integration

Native Browse MCP is **stdio** (`~/.local/bin/browse mcp`). p2 can use it directly.
Executor needs HTTP, so the established pinned **Supergateway 4.2.2** adapter
wraps that same command as stateful Streamable HTTP, not custom CDP plumbing.
User `browse-mcp.service` binds **127.0.0.1:19989**; the only private HTTPS route is
`https://browse.pi.jackharrhy.dev/mcp`. There is no root/raw-CDP route. It is a
permanent integration, not an expiring temporary preview lease.

Every adapter request requires the inbound API key read via `--apiKeyFile` from
`~/.local/share/browse/mcp-api-key` (0600), distinct from relay/browser keys. The
helper creates a key only if absent; never rotate a configured account implicitly.
Use the supported Executor provider-account secret form to provision its bearer
credential with exact HTTPS host placement. Do not use `--oauth2Bearer` (outbound
credential), inline argv keys, wildcard CORS, public bind or an unauthenticated
HTTP browser endpoint. Missing/unreadable/empty key files fail closed. The supported
log levels are `debug`, `info`, `none`; the unit uses `none` to avoid browser data
in adapter logs. Pairing and tool approval/lent-tab consent remain separate gates.

Install the reviewed launchers/units with normal `install`, then enable user
`browse-relay.service` and `browse-mcp.service`; do not start competing upstream
daemons/installers. Check service state, localhost unauthenticated API 401,
Tailnet remote API 404/foreign extension Origin 403, missing/wrong MCP key 401,
authenticated MCP initialize, and independent public WAN TCP/Host/SNI denial.
Never claim a working browser until the owner really pairs/lends a tab. Logs,
journals, browser keys and captured private content stay outside Git in Browse's
XDG folders; upstream journals are bounded to fourteen days/200 entries, not a
promise of zero retention or protection from the Unix account.

## Lore

Official Lore 0.11.0 serves `grpcs://lore.jackharrhy.dev:443`, repository `gldsrc`
(PT sources under `pt/`). Mug routes gRPC over h2c to Newport's tailnet port 41337;
health is loopback 41339 `/health_check`. No extra router forwards are required.
The digest-pinned service is deliberately excluded from Watchtower.

`hosts/newport/lore/local.toml` holds the issuer/client/project audience/JWKS and
`lore_roles` contract. Access requires an explicit Lore grant; server repositories
are shared among assigned users, not protected by per-repository ACLs. Signed
tokens remain usable until expiry, and this client version may need a new browser
login rather than automatic token refresh. Credentials belong in private Auth
runtime/operator storage, never map files.

```sh
infra refresh newport --service lore
```

Changing mounted `local.toml` also requires `docker compose restart lore` from
`hosts/newport`: file-content changes alone do not trigger recreation. Coordinate
editing first; restart clears in-memory file locks. Back up
`/mnt/terrabud/docker-data/newport/lore` while stopped and retain an off-host copy.
Keep history/recovery archives; do not treat a renamed repository as a supported
native operation or reuse retired identity-provider configuration.

Obtain editable Lore checkouts through the supported client; the server's backing
store is not a working tree. Keep repository identity/history and native lock
semantics intact rather than editing backing files to imitate a client operation.

## Browser policy diagnostics

A legitimate flow can fail because response policy produces `Origin: null` or
CSP blocks a verified post-consent callback. Reproduce the actual browser request
and fix the responsible, narrowly scoped response/redirect policy; do not drop
CSRF/origin validation, reuse a one-time consent handle or broaden arbitrary
redirects to make the symptom disappear. Successful anonymous redirects alone
still do not establish a working human authorization flow.

# Jack Auth

Public issuer and custom UI: https://auth.jackharrhy.dev.
Git checkout on Newport: `~/repos/personal/auth`. The separate
`~/repos/personal/jack-auth` directory is the deployment source copy. See the
checkout's README for scope, tests, credentials and deployment instructions.

Services in ../compose.yml: jack-auth-db (private PostgreSQL17), jack-auth-api
(ZITADEL4.20.0 pinned by digest), jack-auth-ui (locally built jack-auth:spike).
Mug's `traefik/dynamic/routes.yml` splits the custom UI and provider API.
Published backend ports18085/18086 bind only Newport's Tailscale IP.

Only secrets/*.enc.yaml is public-safe. scripts/render-secrets.sh newport decrypts
to ignored .runtime-secrets. JSON credential wrappers use the top-level json key.
The UI container runs uid1000; its token files must be owned/readable by that uid,
mode0600. The bootstrap instance-owner PAT never enters the UI container.

Provisioning and live acceptance scripts are in the jack-auth source repository.
The private provision.json checkpoint and jack/joel-login.txt files must never be
committed. The UI uses separate service-account RSA keys to obtain short-lived API tokens.
Encrypted login-key.json and management-key.json files are mounted read-only.
Provisioned keys last one year; scheduled key rotation remains pending.
Application provisioning uses a separate encrypted operator key, never mounted
into the UI. Historical PAT-based scripts are not the current provisioning path.

ZITADEL sends through SES in production account `714000190305`, `us-east-1`,
using the dedicated SMTP identity in `aws/mail/index.ts`. It can send only as
`auth@jackharrhy.dev`, with STARTTLS at `email-smtp.us-east-1.amazonaws.com:587`.
The active provider uses `secrets/smtp.enc.yaml`; render its ignored runtime file
with the existing secrets renderer. Auth owns provider and SMTP configuration.
Real verification/recovery emails and redeemed links passed acceptance, including
SPF, DKIM and DMARC. Lists and its subscriber store are independent.

Email verification and password recovery UI pass live disposable-account tests.
PBKDF2 import verification is enabled for legacy 4orm hashes; new passwords keep
the default bcrypt hasher. All 61 existing 4orm accounts have been imported or
explicitly linked; browser login and member invites use the central issuer.
Jack and Joel reached their original profiles through live OIDC and SSO checks.

Artbin and Tea Maps have central OIDC/resource-server clients and per-app member/
admin grants. Artbin browser/CLI/API/MCP and the Maps-to-Artbin machine caller
were cut over on Oct29 using Tea merge 103d285205ca631415a4ebc86750c3c8ce2b1913.
That image pin was temporary. Artbin and Worldview now follow their canonical
Harrhy `latest` images with Watchtower enabled; check Compose and the actual image
revision rather than restoring the old cutover pin. Artbin loads
artbin-central-auth.env. Worldview's service loads maps-artbin-auth.env for its
limited asset-read/content caller; its browser/MCP now use Jack Auth directly.

Before publication, Watchtower was stopped and old images tagged
tea-artbin:before-jack-auth-20261029 and tea-maps-service:before-jack-auth-20261029.
Consistent online and fresh stopped-app databases plus private rollback container
configuration were encrypted under
/mnt/terrabud/backups/jack-auth/tea-cutover-20261029T143104Z/.
Both stopped snapshots decrypted byte-identically; SQLite integrity passed.
The reviewed mapping converted all 36 Artbin subjects before migration 0006 while
preserving 36 user IDs, 1165 folder ownership records and 72855 file records/FKs.
No Maps browser identity rows changed.

Live browser/CLI login for Jack and Joel preserves their original local accounts;
admin/MCP denies Joel, CLI handoff replay is denied, and machine credentials can
read catalog/content but cannot administer MCP or read content without its scope.
A disposable dynamically registered client completed explicit Jack consent and
called the real production MCP API. Maps browser login through 4orm/central SSO and
the new server-side Artbin catalog caller passed. No assets/projects were modified.
Operational checkpoint (private, contains secrets):
jack-auth/.runtime-secrets/tea-cutover.json; acceptance fixture is alongside it.
Stop both apps before rollback, preserve current databases for later reconciliation,
and use the encrypted stopped snapshots, old image tags and original environment
from that checkpoint together. Never start an old image against the new schema or
restore identities independently of the image/environment.

Explicit third-party Artbin/Maps administrator consent is deployed as of Oct29.
Open dynamic client registration is enabled behind Mug's watched registration
router: 16KiB request bodies, six source requests/minute (burst3), and 30 total
requests/hour (burst10). Source addresses come from the socket, not forwarded
headers. Docker aggregates IPv6 sources under its bridge gateway; they share
the source limit, while IPv4 sources are distinct. Registration management uses
the same limits. `scripts/configure-dcr.py disabled` in the auth checkout
disables registration while preserving iframe and impersonation settings.

The dedicated ZITADEL DCR project defines the `admin` role so ZITADEL retains
the explicit role scope in authorization requests. No DCR user grants were
assigned; consent requires an existing active admin grant on the target app.
Keep DCR automatic role assertion disabled. Disposable live checks passed
approval/denial/CSRF, PKCE, signed ID token/nonce, exact project audiences/scopes/
roles, code/decision replay, refresh/revocation and grant changes after viewing.
The initial Artbin production API/MCP acceptance passed. Worldview's later Jack
Auth configuration is deployed at worldview.harrhy.xyz; genuine human/delegated
acceptance must be read from current owner receipts, not inferred from redirects.
Provider backup before these changes:
`/mnt/terrabud/backups/jack-auth/before-consent-2026-10-29.sql.age`.

ZITADEL DB: /mnt/terrabud/docker-data/newport/jack-auth/postgres.
Preserve the encrypted master key with PostgreSQL backups; losing it prevents
recovery of encrypted provider data. Encrypted provider/4orm snapshots also have
off-host copies on Jack's Mac. Automated retention and full provider startup
from restored data remain pending.

## Radio enrollment ledger

The read-only UI has one dedicated writable mount:
`/mnt/terrabud/docker-data/newport/jack-auth/ui:/data`.
The host directory is UID1000 mode0700; `RADIO_ENROLLMENT_DB_FILE` points to
`/data/radio-enrollment.sqlite`, mode0600. Preserve the directory across every
recreation. Losing/resetting this ledger can lose enrollment-denial history;
it is authorization state, not cache. Existing credential mounts stay read-only.

The redesigned UI also stores groups, provenance, blocks and operations in
`/data/access.sqlite` (UID1000, mode0600, DELETE journal), without passwords. It
shares the existing writable mount. The deployed, disabled support-login code can
also store encrypted lifecycle/token material there when separately configured;
that future activation requires its matching sealed configuration/encryption key
in recovery. The paired database helper alone does not back up that new key.
`ACCESS_DB_FILE`, when set, overrides that path; otherwise the UI derives it from
the parent of `RADIO_ENROLLMENT_DB_FILE`.

`backup-radio-ledger.py` snapshots the Radio ledger and its sibling `access.sqlite`
when present, using SQLite's online backup API and integrity checks. An optional
`--access-source` supplies an overridden host path. Radio keeps the existing
`<run>.sqlite` filename; access uses `<run>.access.sqlite`. A completed `<run>.json`
manifest identifies the recovery set. Source database bytes/inodes are not replaced.
Before first adoption, the manifest explicitly records access as absent; that is
only a legacy baseline, not a complete redesigned-UI checkpoint. Once access has
been captured, `.access-required` makes later missing access fail closed instead
of silently producing a Radio-only checkpoint. Preserve that marker with recovery
history. Snapshots/manifests are mode0600 beneath the private mode0700
`/mnt/terrabud/backups/jack-auth/radio-ledger` directory, without automatic deletion.
Each database is individually SQLite-consistent online; for one logical point
across both files, the Auth runtime owner must quiesce UI writes while running the
helper. Primary must not stop/recreate the UI during Auth's exclusive writer lane.

`radio-ledger-backup.cron`, installed as `/etc/cron.d/jack-auth-radio-ledger`,
runs daily at04:17 host time and logs failures in that private backup directory.
Run the helper before scoped UI maintenance too. For recovery, stop the UI,
preserve the current files, and restore both members of the reviewed manifest as
UID1000 mode0600 under the existing mode0700 parent. Restore access groups,
provenance, blocks and operations together with the corresponding Radio history;
do not silently replace adopted access state with a pre-adoption absent baseline. Recover with the matching provider
checkpoint and credential configuration; do not replace a later denial ledger
with an old empty copy or interpret a ledger-only snapshot as full issuer recovery.
Verify SQLite integrity and membership states before restarting. Persistence
configuration does not activate Radio or any held consumer client.

ZITADEL core is AGPL; the separately authored UI is MIT and the Lore token action
is AGPL. No ZITADEL source was modified. See upstream LICENSING.md at v4.20.0.

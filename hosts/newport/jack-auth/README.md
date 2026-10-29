# Jack Auth

Public issuer and custom UI: https://auth.jackharrhy.dev.
Git checkout on Newport: `~/repos/personal/auth`. The separate
`~/repos/personal/jack-auth` directory is the deployment source copy. See the
checkout's README for scope, tests, credentials and deployment instructions.

Services in ../compose.yml: jack-auth-db (private PostgreSQL17), jack-auth-api
(ZITADEL4.20.0 pinned by digest), jack-auth-ui (locally built jack-auth:spike).
Mug's watched Traefik file jack-auth.yml splits the custom UI and provider API.
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
Legacy acceptance/provisioning PATs expire2026-11-25UTC and the bootstrap owner
PAT expires2026-11-01UTC. Ongoing application provisioning now uses a separate
operator key (encrypted, never mounted into the UI); remaining legacy scripts
still need migration before retiring those PATs.

SES SMTP is configured directly in ZITADEL using the dedicated jack-auth-mail IAM
identity defined in aws/index.ts. It can send raw email only from
 auth@jackharrhy.dev through the verified jackharrhy.dev identity in us-east-1.
The policy also permits the default SES configuration set. STARTTLS, SMTP login
and simulator/real sends passed; Jack confirmed non-Gmail inbox delivery. Gmail
delivery and actual notification-link delivery are still being checked.
The existing lists campaign service and its subscriber store are not involved.

Email verification and password recovery UI pass live disposable-account tests.
PBKDF2 import verification is enabled for legacy 4orm hashes; new passwords keep
the default bcrypt hasher. All 61 existing 4orm accounts have been imported or
explicitly linked; browser login and member invites use the central issuer.
Jack and Joel reached their original profiles through live OIDC and SSO checks.

Artbin and Tea Maps have central OIDC/resource-server clients and per-app member/
admin grants. Artbin browser/CLI/API/MCP and the Maps-to-Artbin machine caller
were cut over on Oct29 using Tea merge 103d285205ca631415a4ebc86750c3c8ce2b1913.
Compose pins both target images to that merge SHA and excludes them from
Watchtower; the normal updater runs for other services. Artbin loads
artbin-central-auth.env. Maps loads maps-artbin-auth.env and AUTH_ISSUER for its
limited asset-read/content caller, while its browser/MCP still use 4orm.

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
Artbin production API/MCP acceptance now passes; Maps own central browser/MCP migration remains pending.
Provider backup before these changes:
`/mnt/terrabud/backups/jack-auth/before-consent-2026-10-29.sql.age`.

ZITADEL DB: /mnt/terrabud/docker-data/newport/jack-auth/postgres.
Preserve the encrypted master key with PostgreSQL backups; losing it prevents
recovery of encrypted provider data. Encrypted provider/4orm snapshots also have
off-host copies on Jack's Mac. Automated retention and full provider startup
from restored data remain pending.

ZITADEL core is AGPL; the separately authored UI is MIT and the Lore token action
is AGPL. No ZITADEL source was modified. See upstream LICENSING.md at v4.20.0.

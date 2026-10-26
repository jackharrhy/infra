# Jack Auth spike

Public issuer and custom UI: https://auth.jackharrhy.dev.
Source checkout on Newport: `~/repos/personal/jack-auth`; see its README for
scope, tests, credential lifetimes and deployment instructions.

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
PAT expires2026-11-01UTC; operational scripts still need migration.

SES SMTP is configured directly in ZITADEL using the dedicated jack-auth-mail IAM
identity defined in aws/index.ts. It can send raw email only from
 auth@jackharrhy.dev through the verified jackharrhy.dev identity in us-east-1.
The policy also permits the default SES configuration set. STARTTLS, SMTP login
and simulator/real sends passed; Jack confirmed non-Gmail inbox delivery. Gmail
delivery and actual notification-link delivery are still being checked.
The existing lists campaign service and its subscriber store are not involved.

Email verification and password recovery UI pass live disposable-account tests.
PBKDF2 import verification is enabled for legacy 4orm hashes; new passwords keep
the default bcrypt hasher. Only disposable migration accounts have been tested.

ZITADEL DB: /mnt/terrabud/docker-data/newport/jack-auth/postgres.
Preserve the encrypted master key with PostgreSQL backups; losing it prevents
recovery of encrypted provider data. Set up off-host retention before wider use.

ZITADEL core is AGPL; the separately authored UI is MIT and the Lore token action
is AGPL. No ZITADEL source was modified. See upstream LICENSING.md at v4.20.0.

# Executor

Executor's self-host server runs as `executor` in Newport's main Compose project,
independently of Chum. The pinned release is `2.0.0-beta.37`.

- Dashboard: https://executor.jackharrhy.dev
- MCP: https://executor.jackharrhy.dev/mcp
- Data: /mnt/terrabud/docker-data/newport/executor/data
- Host-local health probe: http://127.0.0.1:4400/health

The existing owner is linked to Auth and initial setup is closed. Sign in through
Auth; password authentication is disabled. The temporary Serve endpoint at
port 8466 is retired; changing origins requires a fresh browser sign-in.

## Routing and authentication

Wildcard jackharrhy.dev DNS points to Mug. Mug terminates HTTPS using its
existing certificate and forwards this host over Tailscale to Newport's Traefik,
which sends it over `newport_web` to container port 4400. The Mug route is
`hosts/mug/traefik/dynamic/executor.yml`. Docker publishes only loopback port 4400.

`BETTER_AUTH_URL` must match the public HTTPS origin exactly. The whole hostname
is forwarded, including `/mcp`, `/.well-known/*`, `/mcp/authorize`, and
`/api/oauth/callback`. Executor owns local sessions, organization access, MCP
OAuth, and PATs. Do not put another interactive forward-auth login in front of those paths.
OIDC SSO is the only enabled sign-in method; `/login` starts it automatically.

The generated Executor management app also embeds its installation origin in
`index.ts`, `openapi.json`, and `provider.ts`. Changing `BETTER_AUTH_URL` does not
rewrite that saved app. On an origin change, update and deploy its source through
the app API, then reconnect its service account if the provider identity changes.
The public-origin repair is app source commit
`2646b5bcdaca8a7d1f0d7780ea65b0b4d351d69e`, deployment
`dpl_0656386c-3399-4d27-89c4-ad1937089cc6`; owner and app identity were retained.

## SSO integration contract

Auth owns the dedicated Executor confidential OIDC web client, project eligibility
and provisioning. Executor owns local accounts, organization roles, dashboard
sessions and MCP authorization. Chum's Pi/model authentication stays separate.

- Issuer: `https://auth.jackharrhy.dev`
- Discovery: `https://auth.jackharrhy.dev/.well-known/openid-configuration`
- Callback: `https://executor.jackharrhy.dev/api/auth/callback/sso`
- Authorization code, client_secret_post, PKCE S256, state and nonce; scopes
  `openid email profile`. No refresh grant, offline access or delegated role scopes.

Use native signed-in account linking to retain the existing owner's user,
organization and management app. Do not introduce email-based merging or relax
provider trust/email matching. Confirm the owner's verified email, eligible Auth
subject and allowed domain before provisioning. The existing owner email has now
been privately matched to the confirmed, active Auth subject with verified email;
identity edits are unnecessary. The mode-600 reference is
`.runtime-secrets/owner-alignment.json` (ignored by Git).
Initial Auth eligibility is limited to the operator-confirmed existing owner
subject; domain membership alone grants no access. Any further Auth eligibility
grants require a separate access decision. Newly eligible verified identities
within the allowed domain can natively join Executor as members, never owners.

Executor's domain/verified-email checks govern new-user admission. Existing-member
sign-in and account linking must not be described as enforcing those checks on
every request. Auth roles do not confer Executor owner/admin privileges.

Auth owns `hosts/newport/secrets/executor-sso.enc.yaml`, containing
`SSO_CLIENT_ID` and `SSO_CLIENT_SECRET`, rendered to ignored
`hosts/newport/.runtime-secrets/executor-sso.env` with mode 600. The consumer
integration owns the Executor Compose stanza and nonsecret `SSO_DISCOVERY_URL`
and `SSO_ALLOWED_DOMAINS`, referencing that env file. No Auth operator credential
enters Executor. Secret rotation requires coordinated provisioning and restart;
there is no assumed automatic rotation or expiry.

Disabling the Auth client/grant blocks new SSO, not existing Executor sessions,
MCP tokens or local credentials. The final SSO-only mode disables password access
independently. MCP access tokens last one hour and refresh tokens 30 days in the
pinned source. Dashboard sessions default to seven days, with a one-day update
interval in Better Auth 1.7.16. The patch sets native
`disableProviderLogout: true`: sign-out revokes the local session and returns to
`/` without invoking provider logout. Auth cookies remain independent.
Executor-local revocation is a separate operation.

Before rollout, verify pinned client behavior for PKCE, state, nonce, ID-token
issuer/audience/expiry/subject validation and matching UserInfo subject. Acceptance
requires signed-in owner linking followed by fresh-browser SSO to the same owner,
organization and app without duplicates; no-grant, unverified, wrong-domain and
link-collision cases; password endpoints refused after cutover; grant revocation
blocking new SSO; wrong-state/nonce/PKCE cases; and native public MCP
consent/token/resource access. Record existing-session behavior rather than
assuming global logout. Jack authorized implementation and the staged SSO-only
cutover. Existing-owner linking and fresh sign-in were verified before disabling
passwords. Remaining acceptance cases are listed below.
No new identities or access grants may be guessed from an email domain.

## Auth-only build and cutover

`build.sh` builds `local/executor:2.0.0-beta.37-auth-only.1` from upstream commit
`b31108468cf5e3857f00788eac809480a7371466` plus `sso-only.patch`. The Dockerfile
rebuilds the Worker/UI and retains the pinned upstream native runtime. No Chum
code or proxy authentication layer is involved.

The editable upstream checkout is `/home/jack/repos/contrib/executor`, branch
`jack/sso-only`, local commit `657289a`. The deployment build uses a clean pinned
checkout plus the exported patch; editing the development checkout alone does not
change the running container.

The patch adds `SSO_ONLY=true`: native password sign-in and password management
endpoints are disabled, password-based setup/invitation registration is refused,
and `/login` starts native SSO automatically. Callback errors show an explicit
retry instead of looping. Missing SSO configuration fails startup; unavailable
discovery cannot restore password access. Implicit account merging is disabled;
explicit signed-in linking keeps native verified-email and collision checks.
Native provider logout is disabled so signing out here does not sign out other
Auth consumers.

Auth and the consumer are live with `SSO_ONLY=true`. Jack completed SSO. A fresh
read-only database snapshot confirms exactly one user, the original owner and
organization, the intended Auth subject linked to that owner, and the original
management app under the same organization. A fresh session follows the provider
account update. Native verified SSO changed the local email-verification flag;
no identity or email flag was manually edited.

Public browser checks confirm automatic Auth redirect with the exact callback,
PKCE S256, state and nonce. Password endpoints return 404; public health and MCP
discovery pass, and anonymous MCP remains rejected. Jack reported unreliable
return navigation after central login across Executor, 4orm and Artbin; Auth owns
that investigation. A full native MCP consent/token/resource round trip, live
nonce/PKCE negatives and authenticated logout isolation remain unverified.

The encrypted stopped-volume snapshot is
`/mnt/terrabud/backups/executor/before-sso-20261106T192602Z.tar.gz.age`; decryption
and archive integrity checks pass.

Stage with SSO configured and `SSO_ONLY=false` long enough for the existing owner
to connect Auth from `/account/security`. Verify a fresh browser reaches the same
owner user, organization and management app before setting `SSO_ONLY=true`.
Then verify direct password/registration requests are refused and MCP still works.
An operator can roll back the image/configuration using the same data volume;
there is no browser password fallback in the final configuration. Back up first.

## Operations

From `hosts/newport`:

```sh
docker compose ps executor
docker compose logs --tail=100 executor
docker compose restart executor
docker compose stop executor
docker compose up -d --no-deps executor
```

For this local patched image, run `hosts/newport/executor/build.sh` from the repo
root before `docker compose up -d --no-deps executor`. Compose never pulls the
local image tag. Do not use the registry-pull refresh path for this service.
The container uses `restart: unless-stopped` and its native health check.
Watchtower is disabled for this pinned release.

The image contains the dashboard, API, auth, MCP, app runtime, and embedded
PGlite database. It fixes volume ownership before running as its unprivileged
executor user. It has no Docker socket or home-directory mount. Product analytics
are disabled; bundled Motel telemetry is ephemeral and separately bounded.

Stop the container before a filesystem backup of the whole data directory.
Preserve permissions and the generated `auth-secret.key` and `encryption.key`;
database files alone cannot recover encrypted service accounts. Back up before
changing the image version, then recreate with the same data directory.

The previous single-user CLI server has a different storage format. Its data is
retained in `.runtime-secrets/local-cli-data`, outside Git and not mounted into
this server. Its standalone installation and systemd unit have been removed.

## Optional capabilities

App web pages need `EXECUTOR_APP_UI_BASE_URL`, for example
`https://executor-apps.jackharrhy.dev`, plus wildcard DNS and a certificate for
`*.executor-apps.jackharrhy.dev`. The existing `*.jackharrhy.dev` TLS certificate
does not cover that extra label. Dashboard and MCP need only the current host.

`EXECUTOR_OAUTH_CLIENT_METADATA_URL` can publish
`https://executor.jackharrhy.dev/oauth/client-metadata.json` for providers that
accept public client metadata documents. It is not enabled yet.

Private-network fetch stays disabled by upstream default. Enable
`EXECUTOR_APPS_ALLOW_PRIVATE_FETCH=true` when an integration needs a private
MCP/API service; every app in the instance then has that network position.

## Verification and references

The Auth-only image passes isolated container/browser checks: password routes
return 404, setup and invitation registration return 403, invalid SSO callback
state creates no session, and login automatically starts one PKCE S256/state/nonce
transaction. A callback refusal shows a retry without password inputs or a redirect
loop; retry starts a new transaction. Missing required SSO configuration fails
closed, and unreachable discovery does not restore password routes. MCP discovery
remains available and anonymous MCP access returns 401. Focused server/web type checks, formatting and lint pass.
These checks use a dummy client and intercept the authorization navigation; they
do not establish real owner linking, Auth eligibility, or the full MCP consent flow.


Owner setup retained after origin change; healthy container; keys persisted
across restart; dashboard and both OAuth discovery documents reachable through
HTTPS; unauthenticated MCP rejected. Authenticated MCP skill inventory and skill
file retrieval pass after the management-app origin repair. Browser OAuth client authorization still needs
an end-to-end check after signing in on the public origin.

- https://executor.sh/docs/run/self-host
- https://executor.sh/docs/concepts/organizations-and-access
- https://executor.sh/docs/mcp

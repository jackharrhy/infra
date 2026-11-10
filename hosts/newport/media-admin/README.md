# Media administration

- https://sonarr.rotund.org — TV library and missing episodes
- https://prowlarr.rotund.org — indexers and release searches
- https://qbittorrent.rotund.org — downloads and transfer controls

Mug terminates HTTPS and relays these hosts to Newport. Each Newport router uses
Traefik ForwardAuth with its own OAuth2 Proxy instance. The issuer is
`https://auth.jackharrhy.dev`; only the reviewed Jack subject has the dedicated
Media Admin project grant. The proxy additionally allows only that immutable
signed `sub`, not an email domain or arbitrary logged-in account.

Each client has one exact `/oauth2/callback`, authorization code with S256 PKCE,
explicit nonce verification, no refresh grant, and a one-hour host-only Secure,
HttpOnly cookie. Cookies and client secrets are separate for each application.
Disabling a provider client blocks new logins; existing proxy sessions can last
until expiry. For immediate removal, rotate that proxy's cookie secret and reload
it as well. Do not pass tokens or trusted identity headers into the native apps.

## Native applications and private automation

Direct Tailnet UI bindings are removed. Loopback ports 8989, 9696 and 8087 remain
for maintenance, backups and local automation; containers use private service DNS.
The public API paths have the same central-auth gate as the UI, even with an API
key. Keep automation on private addresses rather than adding public bypass routes.

Sonarr and Prowlarr use native `External` authentication behind the gate. Their
API keys are unchanged. qBittorrent bypasses its native login only for the exact
Newport Docker web bridge gateway (`172.21.0.1/32` at setup); forwarded client-IP
trust remains disabled. Other private callers still use native credentials.
Host-header validation and CSRF protection remain enabled, with
`qbittorrent.rotund.org` explicitly added to the existing allowed host list.
Recheck the gateway if recreating the Docker network; do not whitelist an entire
subnet or disable those checks to fix a proxy error.

Settings live in the existing native application volumes. Take native backups
before changing them. Source secrets are `secrets/{app}-auth.enc.yaml`, rendered
to mode-0600 `.runtime-secrets/{app}-auth.env`; neither values nor session cookies
belong in this documentation. Auth owns provider resources and registry policy.

The temporary media review dashboard is retired. Its notes, inventory and cleanup
outcomes remain private records, not another public application.

## Verification

Check an actual owner login reaches each UI, an existing no-grant identity is
denied, malformed callbacks cannot create a session, and anonymous/spoofed-header
requests cannot reach either UI or API. Preserve the native backup hooks, download
caps, stopped seeding state and current library. Test source with:

    uv run python -m unittest discover -s tests -p 'test_*media*.py'
    uv run python -m unittest discover -s tests -p test_sonarr.py

The shared watcher remains enabled; no temporary image pins or exclusions are used.

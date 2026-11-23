# Private Hosting authentication edge

Newport's exact Tailnet routers send Atlas and Go Demo to the loopback edge on
port 21980. The edge requires the exact owner subject before dialing Caddy's
permissioned Unix socket. The two OAuth listeners are loopback only and use
independent host-only cookie keys with the shared Jack Auth client. Caddy never
receives edge cookies, tokens or user identity.

Slides uses a dedicated Tailnet-only route on loopback port 21984. It permits
anonymous viewing; the application owns presenter authentication and writes.
Only the documented app paths and native Slides cookies pass to Caddy. Operator
paths and gateway OAuth paths are excluded. Caddy must preserve the exact
external Slides host and HTTPS scheme to the native app. Install or update this
edge independently with `bash hosts/newport/private-hosting-auth/install.sh --slides`.

Run `bash hosts/newport/private-hosting-auth/install.sh` as Jack on Newport. It
requires the existing private `~/.local/state/infra/private-hosting-auth/provider.json`
and preserves the host-specific cookie keys on reinstall. The Auth UI's active
`AUTH_APPLICATIONS_FILE` registry needs an additive `private-hosting` entry with
the dedicated project and client, PKCE and owner role requirement. Apply that
entry without replacing unrelated entries; restart only `newport-jack-auth-ui-1`
if the registry changed. Do not publish the provider file or generated runtime
configuration.

Before exposing a new backend, verify the exact host over the Unix socket and
confirm anonymous HTTPS is denied or redirects to Jack Auth, with an exact
same-host callback. Verify a real owner browser session separately. To withdraw
access, remove only these exact routers from the canonical routes file first;
never substitute a direct Caddy listener.

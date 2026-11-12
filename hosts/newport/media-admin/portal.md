# rotund.org portal

The root site is a native Remix 3 application from `jackharrhy/harrhy` (`apps/rotund`),
served on container port80. The funny face is preserved byte-for-byte; static UI
styles use Remix `css(...)` mixins, typed routes and controller-owned views.

Portal credentials/configuration are SOPS-encrypted in `rotund-portal.enc.yaml`.
The browser gets only a signed Secure/HttpOnly/host-only session-reference cookie;
OIDC access tokens stay in bounded server memory. Sessions may restart after a
container update; central SSO is probed once rather than assuming a shared cookie.
The normal anonymous view offers Sign in without leaking private service links.

The catalogue includes Jellyfin, Sonarr, Radarr, Prowlarr, qBittorrent, optional
Navidrome and Seerr, and publicly playable Gurgur. Both optional bindings use
independent project roles and the exact reviewed Jack subject; Seerr retains its
native Jellyfin login. Every authenticated page reads live UserInfo and filters
protected links by exact project/org/role. Names, email and forwarded headers do
not grant access. Gurgur requires no new central project. Jellyfin's directory role
is separate from its native account: only the already reviewed owner is assigned
initially; another person's visibility needs an explicit central-subject/access
review, never an inferred name/email match. Nothing provisions a Jellyfin account.

Radarr now has an independent owner-only ForwardAuth boundary like the other
media administration apps. Its native API/loopback port remains available for
local automation, with no Tailnet bypass. `radarr-auth.enc.yaml` contains its
separate client/cookie configuration. Retired media-review remains retired.

The directory is not an authorization proxy. Each destination still checks its
own access. Local portal logout does not promise global central-SSO logout.
Production has no application database or business-state migration; recovery
inputs are the source/image and encrypted configuration. Production follows
`ghcr.io/jackharrhy/rotund:latest` with Newport's opt-in Watchtower enabled.
The temporary SHA hold is removed: the same corrected image passed public checks,
and Jack attested that all seven protected links and native Seerr owner login work.
That is operator acceptance, not an automated browser run. Old source, encrypted
config and a verified image archive remain retained for separate retirement.
The issuer callback remains `/auth/callback`, not `/`.

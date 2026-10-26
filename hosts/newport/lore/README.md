# Lore for gldsrc

Public server: grpcs://lore.jackharrhy.dev:443.
Repository: gldsrc, with PT sources under pt/. Official client/server version0.11.0; server pinned
by digest in ../compose.yml. Watchtower is disabled.

Mug Traefik routes HTTPS gRPC via h2c to Newport's Tailscale port41337.
Health binds loopback41339 (/health_check). No home-router forwards added.
Authentication uses ZITADEL at https://auth.jackharrhy.dev and the custom Jack Auth
login UI. Old Keycloak containers, DB, routes and bootstrap secrets are removed.

local.toml specifies the issuer, OIDC client ID, project audience scope, public
JWKS and lore_roles permission claim. The provider project requires assignment.
Jack has owner, Joel editor; new users need an explicit Lore grant through /manage.
The configuration shares this server's repositories with assigned users; it does
not implement per-repository ACLs. Signed tokens keep access until expiry.

Runtime credentials live under jack-auth/.runtime-secrets and the operator's
private ~/.config/jack-auth folder on the Mac. No credentials belong in map files.

Deploy with ~/infra/.venv/bin/python cli.py refresh newport --service lore from
~/infra. Changing a mounted local.toml also needs a scoped docker compose restart
lore, since Compose cannot detect file-content changes. This clears in-memory
file locks; coordinate editing before maintenance. Revision history remains on
/mnt/terrabud/docker-data/newport/lore. Back up that directory while Lore is stopped
and keep an off-host copy. The obsolete Keycloak initial backup was removed.

Both ZITADEL accounts passed device approval, list/clone, matching JMF/MAP hashes
and exclusive lock/handoff checks. Official Desktop remains installed; sign in
again using the new provider. Lore0.11 does not automatically refresh OIDC tokens,
so it may request another browser login after token expiry.

The original horror-map-pack history is archived in /mnt/terrabud/backups/lore/before-gldsrc-2026-10-25.tar.gz.age. Lore 0.11 has no repository rename operation; current content was imported into gldsrc.

The old horror-map-pack server entry was deleted after migration. The current server repository is gldsrc. The temporary legacy-identity claim used for deletion was restored immediately; normal Jack Auth identities are unchanged.

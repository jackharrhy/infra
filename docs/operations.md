# Operations

Run repository commands from `~/infra` unless another directory is specified.
Use the primary checkout and coordinate one source/index writer. Do not use
worktrees, reset a dirty target, or overwrite unrelated live Compose/routing edits
as a shortcut. Live service configuration is authoritative: compare intended
changes with the target before recreation. Inspection is not deployment authority.

## Scoped maintenance and updates

```sh
uv run cli.py install
infra status newport
infra update newport
infra refresh newport --service jellyfin
infra refresh mug --service radio-celld --service teacms
```

`status` compares Git revisions, not service health. `update` pulls target Git only.
Repeated `--service NAME` selects services; scoped refresh pulls and recreates
without dependencies or image pruning. An unscoped `refresh HOST` updates siblings
and prunes unused images: do not use it for ordinary service maintenance. Nested
Cheesetown and Sven Co-op projects are not part of the main Newport stack.
Local images with `pull_policy: never` need their build/Compose procedure instead.

Before a change, inspect the running image ID/revision (not just a moving local
tag), mounts, effective environment privately, current use, and an appropriate
recovery point. Run required backup/drain gates explicitly for manual Compose
recreation: it does not execute Watchtower lifecycle hooks. Brief scoped downtime
is acceptable; ordinary website traffic is not a veto. Warn game players, save,
and stop gracefully. Drain unrecoverable in-memory games/jobs or use a tested
recovery path, including before automatic updates.

Afterward verify the actual running revision, health/protocol response, restart
stability and the affected user/persistence path. A redirect or 401 is not proof
of successful authenticated use. Do not report source changes or old acceptance
records as current deployment acceptance.

First-party applications normally follow the publisher's actual main-built
moving tag (`main` or `latest`). Use immutable pins only for a concrete rollout
need; remove temporary pins/exclusions/pauses when their release condition passes.
Keep deliberate vendor versions/security holds. Leave Watchtower operational;
any remaining hold needs an affected service, owner, release condition and next
step, not a blanket indefinite freeze.

Newport Watchtower is opt-in (`WATCHTOWER_LABEL_ENABLE=true`); preserve explicit
false and unlabeled development exclusions. Mug does not use the same opt-in
selector: inspect its actual labels/policy. Both configurations enable lifecycle
hooks and scan every ten minutes, offset between hosts. Verify effective updater
configuration and scan results, not labels alone. Backup failure exit 75 blocks
protected updates. Watchtower cleanup of replaced images is not authorization
for broad Docker/storage pruning. Preserve the first legacy backup and a valid
current recovery point; deletion, world conversion and credential retirement need
separate scope.

After a Docker daemon restart with live restore, a running Traefik/Watchtower can
retain a stale Docker socket mount. Compare socket inodes, recreate only affected
consumers, and verify provider discovery/updater connectivity.

## Routing

Local container routes belong in Compose labels. File-provider routes, services
and middleware belong in the host's one watched canonical file:

- [Mug routes](../hosts/mug/traefik/dynamic/routes.yml)
- [Newport routes](../hosts/newport/traefik/dynamic/routes.yml)

Do not introduce per-application route fragments. Listener, provider and ACME
settings belong in each host's Compose configuration. Mug normally terminates
public HTTPS and relays Newport hosts through `newport-origin`, preserving Host;
Newport selects the backend. Auth and Lore use dedicated HTTP/h2c backends.
Cheesetown and Jellyfin terminate public TLS on Newport; Jellyfin's Mug fallback
remains restricted to Mug's tailnet origin.

Use application/role names for routers and services, not host/transport suffixes.
Preserve separate hostname routers, explicit priorities and ACME domain groupings;
combining rules can change all three. Share middleware only for shared behavior,
such as Cheesetown's ordered slash redirect/strip-prefix chain; retain independent
rate-limit buckets and certificate resolvers. Garden's low-priority domain aliases
must not overtake higher-priority application paths.

## SOPS and recovery

Only encrypted secret YAML belongs in Git. Rendering needs `sops` and the
appropriate age identity. Edit ciphertext through SOPS; never print credentials,
provider tokens, session cookies, private application content or identity mappings
in logs or documentation.

```sh
sops hosts/newport/secrets/steve.enc.yaml
(umask 077; ./scripts/render-secrets.sh newport)
```

The renderer recursively finds host/project `secrets/*.enc.yaml`/`.enc.yml` and
writes sibling ignored `.runtime-secrets/` files, mode 0600. Use umask 077 so newly
created directories/files start private; preserve the runtime account's required
read access. Ordinary YAML renders dotenv with literal dollars escaped for
Compose. JSON wrappers use a top-level `json` key and render raw JSON; PEM wrappers
use `pem`; htpasswd files have their own rendering. Do not hand-edit generated
files or treat the renderer as a general multiline quoting tool.

Canonical Steve and Ref inputs are `hosts/newport/secrets/steve.enc.yaml` and
`hosts/newport/secrets/ref.enc.yaml`, yielding `.runtime-secrets/steve.env` and
`.runtime-secrets/ref.env` in that host. Keep those names without duplicate
transition-specific secret files. Existing unrelated identifiers are not a reason
to rename endpoints or application namespaces.

For SQLite recovery, stop the owning service, preserve/move aside its entire
current config/database set including WAL/SHM, then restore a reviewed snapshot
into an **empty destination**. Never overlay a main-file snapshot onto old
sidecars or restore into a running database. Restore matching settings, uploads,
authentication/encryption keys, ownership and private modes as a set. Verify
integrity and affected account/data behavior; retain the moved-aside set until
recovery is accepted. An image downgrade may not reverse a schema change; after
new writes, rollback can require reconciliation rather than old-data replacement.
For UI-only rollback, prefer reverting the image instead of erasing newer access
decisions by restoring an older authorization database.

## DNS and Newport DDNS

```sh
infra dns diff jackharrhy.com.
infra dns sync jackharrhy.com.
infra dns dump
```

DigitalOcean credentials are SOPS-backed. `sync` asks before applying. Newport's
[DDNS service](../hosts/newport/ddns/ddns.service) uses native octoDNS dynamic
sources from [dns/config.yaml](../dns/config.yaml), not a separate DNS writer or
cached-IP file. `home.jackharrhy.dev` is the canonical home WAN A record;
`craft.jackharrhy.dev` and `jellyfin.rotund.org` CNAME to it. Point future home
subdomains there, not at Minecraft's hostname. `cheesetown.rocks` keeps its own
dynamic A because a zone apex cannot be an ordinary CNAME beside NS records.

Dynamic A records must not also appear in static zone YAML. The DDNS source ID
is the label (`home`) or empty string for an apex. IPv4 comes from api.ipify.org;
IPv6 is deliberately not published. TTL is 300 seconds. The user timer starts
two minutes after boot and every five minutes thereafter, with up to 30 seconds
jitter; failed runs retry next tick, with a 90-second service timeout.

Run dynamic-zone review on **Newport**, whose public IP is being published:

```sh
uv run --script ~/infra/cli.py dns diff jackharrhy.dev. cheesetown.rocks.
install -d -m 700 ~/.config/systemd/user
install -m 644 ~/infra/hosts/newport/ddns/ddns.{service,timer} ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now ddns.timer
systemctl --user start ddns.service
systemctl --user status ddns.timer ddns.service
journalctl --user -u ddns.service -n 40
```

Add a name's source/zone in `dns/config.yaml`, remove conflicting static A records,
and include its zone in the service's zone list. Both timer and ordinary diff/sync
use the dynamic sources. The timer reconciles whole selected zones: review static
changes before putting them in the live checkout. DNS does not configure router
forwarding or establish external reachability.

## NAS and diagrams

```sh
infra nas login-check
infra nas shares
infra nas search 'whitelist.json' --name-only
infra nas search minecraft --limit 50 --offset 0 --json
infra nas nfs list SHARE
infra nas nfs grant SHARE CLIENT_PATTERN
infra nas nfs revoke SHARE CLIENT_PATTERN --yes
infra diagram
```

NAS credentials are `nas/secrets/synology.enc.yaml`. Search uses DSM's index and
account permissions, not a local crawl; returned paths are not local mount paths.
Grant/revoke are access changes, not read-only inspection. `diagram` writes
`docs/infra.d2` and invokes D2; `--no-render` writes source only.

## Planned

[Useful Docker health reporting](https://github.com/jackharrhy/infra/issues/78)
tracks future application readiness coverage. No fleet health-check rollout is
included in this documentation/configuration cleanup.

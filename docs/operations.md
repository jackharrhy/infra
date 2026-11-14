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

## Update-hook backups

Custom automatic hooks for AdGuard, Cleanuparr, Seerr, qBittorrent and Lists always
make a fresh producer-consistent capture before a pre-update decision. After the
producer's existing integrity checks, byte-identical covered files/relative paths
may reuse the newest managed publication only within 24 hours and after its full
artifact checksum matches. TTL alone never proves a live database unchanged.
Changes, missing/corrupt artifacts or uncertain equivalence require a new
publication. Directory digests cover file bytes, paths and empty directories, not
mtimes; they do not normalize database or API fields. Existing daily pre-check
cadence remains; an update never uses its time-only daily guard.

Jellyfin is an explicit exception: its existing fresh native pre-update hook and
archives remain unchanged, without automatic pruning or equivalence reuse. Native
completion/full ZIP hashing cannot prove complete database export: the upstream
engine can skip rows on enumeration errors, and filenames have second-resolution
collision risk. Before enabling retention, independently validate ZIP entries and
complete database coverage/recovery, and identify a newly created archive without
overwriting or adopting unknown artifacts. Sonarr/Radarr/Prowlarr and Navidrome
retain their native policies; native manual and scheduled retention can differ.

[The shared helper](../hosts/common/backup-retention.sh) keeps the union of the
newest generation on each of the seven most recent observed UTC backup-days and
the three newest generations. Missed nights do not expire older recovery days.
Only a newly completed, producer-validated publication permits pruning. Hidden
`.infra-hook-v1` completion receipts identify owned immutable generations; only
checksum-matching prune candidates may be removed. Changed, corrupt, unknown,
manual and pre-adoption artifacts are preserved, not adopted by filename. There
is no initial historical cleanup or new cron job. A valid current generation is
always retained. Inspect preservation warnings rather than deleting unknown
files or stale locks blindly.

To make a separately retained manual snapshot, explicitly bypass automatic reuse,
receipts and pruning:

```sh
docker exec newport-adguardhome-1 sh /infra/backup.sh manual
docker exec newport-cleanuparr-1 python3 /infra/backup.py manual
docker exec newport-seerr-1 node /infra/backup.mjs manual
docker exec newport-qbittorrent-1 python3 /infra/backup.py manual
# On Mug:
docker exec mug-lists-1 bun /scripts/lists-backup.mjs manual
```

The helper is mounted read-only at `/opt/infra-backup-retention.sh`. For a live
single-file/directory-bind rollout without app recreation, preserve original bind
inodes, install and verify the helper first, then update the mounted script inode
in place while the applicable updater is briefly paused. Compare running and
tracked hashes and restore Watchtower afterward. A read-only AdGuard rootfs may
use the same helper at `/backups/.infra-backup-retention.sh` until its normal
recreation mounts `/opt`; keep both copies checksum-identical during adoption.
Git rename/pull alone does not
refresh a single-file bind; a directory bind can expose edits immediately. The
Compose helper mounts take effect on the next normal recreation.

## Container memory diagnostics

Run `python3 scripts/container-memory.py --project mug` on Mug, or use
`--project newport` on Newport. Add `sudo` if process/cgroup files are unreadable.
The read-only report includes cgroup-v2 resident charge, swap and memory caps;
Docker's usual stats view omits swapped-out memory. Partial reports fail visibly.
Compare with `/proc/pressure/memory`, `/proc/pressure/io` and `vmstat 2 5` before
changing limits: swap occupancy alone does not establish active paging.

## Routing

Local container routes belong in Compose labels. Permanent file-provider routes,
services and middleware belong in the host's canonical file:

- [Mug routes](../hosts/mug/traefik/dynamic/routes.yml)
- [Newport routes](../hosts/newport/traefik/dynamic/routes.yml)

Do not introduce per-application route fragments. The sole temporary-route
exception is Newport's CLI-generated, Git-ignored `previews.runtime.yml` described
below; never hand-write arbitrary preview YAML. Listener, provider and ACME
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

### Private Pi and named previews

`pi.jackharrhy.dev` and `*.pi.jackharrhy.dev` have explicit Tailnet A records,
not the public wildcard's A/AAAA. Newport Traefik binds `pitailnet` to
`100.123.66.70:443`; only explicit private Host routers use that entrypoint. Public `websecure` stays on `192.168.2.30:443` for
existing WAN forwarding. Keep `web` and `websecure` as explicit default
entrypoints so implicit Docker routers do not inherit the private listener.
A public Host/SNI or spoofed forwarded header must never select the Pi backend.

The private route proxies loopback port 8788, preserves Host/Origin and WebSocket
upgrades, and overwrites `X-P2-Proxy-Secret: 1`. p2 retains its own remote owner
authentication, allowed-host/origin checks and local-only ingress restrictions.
p2's runtime owner maintains its preferred URL/allowed hosts; Infra owns DNS/TLS
and proxy routing. This is the canonical external URL; legacy Tailscale Serve
8788 is retired. Backend loopback port 8788 remains the required proxy upstream.

Traefik's `newportdns` resolver renews DNS-01 certificates using the encrypted
`secrets/traefik.enc.yaml` input and private persisted `acme-dns.json` (0600).
The certificate includes both `pi.jackharrhy.dev` and `*.pi.jackharrhy.dev`;
the wildcard covers one label, not nested subdomains. No public
application/challenge listener is needed. The zone's `pi-acme`
processor excludes only `_acme-challenge.pi` from octoDNS/DDNS reconciliation so
renewal TXT records remain Traefik-owned. Run dynamic-zone DNS changes on Newport,
not Mug. Public DNS and certificate transparency disclose the hostname; they do
not grant service access. Clients require Tailscale and a resolver accepting the
CGNAT answer. Do not replace this with a public Mug route or Tailscale Funnel.

Named previews are opt-in, not a catchall proxy or process launcher:

| Name under `pi.jackharrhy.dev` | Fixed loopback upstream | Application owner / access |
| --- | --- | --- |
| `alderpoint` | 5173 | Alderpoint app; native login and exact allowed host |
| `alderpoint-api` | 54321 | Alderpoint main Supabase; existing API/auth policies |
| `4orm` | 18954 | Harrhy native review; Tailnet entrance, native app login retained |
| `wonder` | 18810 | Wonder static Astro publication; Tailnet read access, independent of p2 |
| `browse` (`/mcp` only) | 19989 | Permanent authenticated Browse MCP adapter; native extension uses separate Tailnet port 19988 |

Permanent registrations have an owner, fixed loopback port and access policy in
the canonical file. Short-lived previews use the local registry below instead of
Infra commits per preview. Reserve the apex for p2; never derive an upstream from
arbitrary Host input. Unknown
names return 404. p2's marker/auth is not shared preview authentication. Traefik
does not inject Tailscale user identities; do not fabricate those headers or
replace an access policy with trust in client-supplied identity. Preserve Host,
Origin and WebSocket upgrades; keep forwarded-header trust disabled on the private
entrypoint. Cookies must be host-only, not scoped to the shared parent domain;
sibling previews are same-site, so retain CSRF/exact Origin checks.

Change app origins/callbacks through the app owner, verify before removing old
Serve entries, and remove a preview route before its backend port is reused.
The native 4orm review's fixture issuer remains its existing Serve 8565 origin:
issuer+subject links are identity state, not a cosmetic URL rename. Do not remove
that issuer route or rewrite identity rows to tidy a hostname. Its app is reached
at the named host. The review app and fixture issuer intentionally use Tailnet
reachability as their entrance boundary; native application login remains separate.
Keep all five review/access listeners on loopback, the app router on `pitailnet`
only, and the issuer Serve mapping private (never Funnel). This is not production
Auth eligibility or authorization for unrelated previews.

Future shared entrance authentication is tracked in
[issue 85](https://github.com/jackharrhy/infra/issues/85); it is not deployed policy.
Do not replace individual app authentication or broaden cookie scope by implication.

Retired game, Cmd, Marty and visual-review previews are not automatically
relaunched by wildcard DNS. Future relaunch is an explicit app-owner request:
start the retained dedicated runtime/state, add a named fixed route, align exact
origins/access gates and verify. Runtime/state cleanup is separate from routing.

After changes verify valid TLS and authentication from a Tailnet client; public
WAN IPv4/IPv6 Host/SNI denial; local-only ingress and unauthenticated WebSocket
denial; retired Serve entries absent and existing public sites unchanged. A server
probe is not a successful owner browser session. Preserve the LAN lease/address
when changing bindings. If a resolver filters public-to-CGNAT answers or retains
negative cache, diagnose that exact resolver; do not disable rebinding protection
globally or hide the problem with hosts-file entries.

### Temporary preview registry (Newport)

Source owners can register an authorized temporary preview without editing Infra
Git or waiting for a proxy operator. Start the app on **127.0.0.1 only**, then run
from any directory on Newport (`uv run --project ~/infra ~/infra/cli.py` is the
same entrypoint if the shortcut is not on PATH):

```sh
~/.local/bin/infra preview register demo --port 21001 --owner my-project \
  --purpose 'Short UI review' --ttl 24h
~/.local/bin/infra preview list
~/.local/bin/infra preview renew demo --owner my-project --ttl 24h
~/.local/bin/infra preview remove demo --owner my-project
```

Registration returns `https://demo.pi.jackharrhy.dev`. The optional repeatable
`--path /login --prefix /assets/` restricts literal URL paths; without these,
only the exact Host is matched. Inputs are not raw Traefik expressions. Names are
single lowercase DNS labels, no wildcard or nested names. Reserved platform and
permanent names, permanent/admin ports, shared leased ports, non-loopback listeners,
owner takeovers and invalid TTLs are refused. Owner labels coordinate trusted
operators; they do not authenticate same-UID agents. Do not register privileged
local services or assume preview routes grant owner-only access.

Leases default to 24h, maximum 7d, with explicit renewal. The private authoritative
registry is `~/.local/state/infra/previews/registry.json` (0700 parent/0600 files).
A process lock serializes writers, complete candidates are validated, and a single
0600 projection is atomically replaced in the existing directory mount:
`hosts/newport/traefik/dynamic/previews.runtime.yml` (ignored by Git). Generated
routers use only exact opt-in Hosts, `pitailnet`, existing wildcard TLS and fixed
`http://127.0.0.1:PORT` upstreams; callers cannot inject middleware, headers,
filesystem paths or upstream URLs. No p2 marker or fake Tailscale identity is added.

`infra-previews.timer` runs `preview reconcile` at user-service startup and every
minute. Expiry removes **routes only**, never processes, ports, files or data.
Startup/expiry is bounded by timer scheduling and file-provider debounce, not a
hard real-time security cutoff. Reconcile validates registry state and rebuilds
the projection; validation failure preserves last-good config and is visible in
`systemctl --user status infra-previews.service` / its journal. A crash between
registry and projection writes is reconciled on the next run. Monitor failures;
do not infer lease expiry from a broken timer.

Remove the lease **before stopping/reusing its port**; the app owner still owns
runtime and sensitive-data/access safety. Renew only while the review remains
wanted. Persistent deployed apps stay in canonical Infra config. A source agent
sharing the Unix account is not sandboxed by this command; this is a small trusted
runtime registry, not a new authorization/orchestration platform.

To install the one expiry timer (already installed on Newport):

```sh
install -m 644 hosts/newport/previews/infra-previews.{service,timer} ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now infra-previews.timer
systemctl --user start infra-previews.service
```

For a one-time migration, `register --adopt-existing` accepts only an exactly
equivalent non-reserved static route/upstream. Verify the generated route first,
then remove the redundant static stanza and reconcile. This allows overlap without
review interruption; it cannot override a different/permanent route. Only the
Auth synthetic fixture was migrated initially; its owner renews/removes its lease.
No other deployed routes or services are delegated by this feature.

The generated file must stay **top-level** in the watched directory: Traefik 3.7.18
loads nested configuration but does not install recursive file watchers. Do not
replace this with a single-file bind mount (atomic replacement/inode trap), a
nested proxy or per-preview committed fragments. Keep runtime registry/projection
out of public archives; Git ignore is not protection against explicit force-add.

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

## Local gateway and Tailnet changes

Discover the actual default gateway and firmware family before selecting a client
or sending credentials. Prefer supported local CLI/web administration and the
existing router client's README; a fixture passing does not establish compatibility
with the current device. Expose only explicitly requested services, not every
listener. Obtain a complete authenticated mapping baseline before writes; a
partial/guest inventory is not an empty rule set or permission to mutate it.

Keep global-enable and per-rule changes separate. Read back each exact write and
preserve unrelated devices' rules. After uncertain/partial failure, inspect state
before retrying: a failed response does not mean nothing changed. Some RDK web
handlers mutate cleanup state even on GET; use the family-specific safe read path
rather than probing an action handler as if it were read-only. Bell/Sagemcom IDs
and global-toggle semantics are not interchangeable with RDK.

Verify TCP with trusted HTTPS and the real application from an independent network;
for UDP use a protocol response or unique received probe, not successful send.
Packet arrival is not actual voice/game acceptance. Preserve existing Tailscale
Serve mappings and complete approved subnet-route sets; an exit node is not proof
of a gateway subnet route. A topology investigation does not authorize router or
network-wide DHCP/DNS changes.

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
Grant/revoke are access changes, not read-only inspection. Paginate indexed search
against its declared total; a truncated page, missing account permission or unindexed
archive is not proof of absence. Reuse the CLI's authenticated client/TOTP handling
and sanitized cleanup rather than creating another credentials transport.

For a selected large ZIP, authenticated HTTP Range reads can inspect its central
directory and small members without downloading the entire archive; require HTTP 206
before consuming a requested range. Never accept a server ignoring Range as a
silent multi-gigabyte download. Stream tar.gz inspection when appropriate, retain
small recovered members privately, and report interruption/ReadError as incomplete
coverage even if a useful member was recovered. Do not extract arbitrary archive
trees onto live data or publish recovered private identities.

`diagram` writes `docs/infra.d2` and invokes D2; `--no-render` writes source only.

## Planned

[Useful Docker health reporting](https://github.com/jackharrhy/infra/issues/78)
tracks future application readiness coverage. No fleet health-check rollout is
included in this documentation/configuration cleanup.

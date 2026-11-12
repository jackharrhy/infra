# Games

Game projects are separate from Newport's main Compose stack; do not use a whole
host refresh to update them. Follow [operations](operations.md): check actual use,
warn players, save/backup and stop gracefully. Brief downtime is acceptable, lost
unsaved sessions are not. A world conversion, major modpack change, deletion or
router-rule change needs explicit scope. Preserve the first legacy backup and a
current recovery point; never broadly prune game images, worlds or archives.

## Cheesetown

The independent project is `hosts/newport/cheesetown`, Compose name `cheesetown`.
Compose pins Minecraft/Fabric/Java configuration and disables Watchtower for its
services. Durable server state is
`/mnt/terrabud/docker-data/newport/cheesetown/fabric-data`; provisioned mods and
backups are siblings. Keep builds/downloaded JARs outside Git. Read current
[Compose](../hosts/newport/cheesetown/compose.yml) and runtime manifests before an
upgrade; do not substitute a different world format or thin/smoke mod artifact.

From that project directory, inspect usage and coordinate a save before restart:

```sh
docker compose ps
docker compose exec minecraft rcon-cli list
docker compose exec minecraft rcon-cli 'say Server maintenance shortly; saving before restart.'
docker compose exec minecraft rcon-cli save-all flush
docker compose stop minecraft
docker compose up -d --no-deps minecraft
```

The stop has a two-minute grace period. Arrange a successful current backup before
version/world/schema changes, not just a save. Confirm logs/readiness, player
reconnect and the affected mod/web features after maintenance. Do not infer a
successful restore or world conversion from container startup alone.

### Backups and restore

`backup` uses RCON to flush and archives every six hours into
`/mnt/terrabud/docker-data/newport/cheesetown/backups`. Rebuildable JARs, cache,
logs, temporary files and BlueMap web/maps output are excluded; preserve the mod
manifests/configuration/toolchain alongside recovery material. AudioPlayer media
is in `world/audio_player_data`, not a disposable web cache.

After a successful backup, [retain-backups.sh](../hosts/newport/cheesetown/retain-backups.sh)
keeps all rolling archives for seven days, the first per day from seven to 28 days,
the first per ISO week thereafter indefinitely, and the earliest surviving rolling
archive indefinitely, using Newfoundland time. Only matching top-level
`cheesetown-*.tar.gz` files are eligible; deployment/retirement/upgrade archives
are untouched. Failed backups skip retention. Preview from the project directory:

```sh
docker compose exec backup /retain-backups.sh --dry-run
```

For recovery, stop the game and backup writer, move the current complete data tree
aside, inspect/extract a reviewed archive into an empty destination, and restore
matching mod/config/image versions and permissions. Do not overlay an old world
onto a newer live tree. Preserve the original until world/player/mod acceptance;
a new-format world is not safely downgraded merely by changing the image.

### Fabric mods and datapacks

Manifests:
[server mods](../hosts/newport/cheesetown/fabric-mods/runtime-manifest.json) and
[datapacks](../hosts/newport/cheesetown/fabric-mods/datapacks-manifest.json).
At startup itzg copies `/mods` into `/data/mods` and source configs into
`/data/config`. Provision from the Infra root:

```sh
uv run scripts/provision-cheesetown-mods.py --custom-dir /path/to/custom-builds
```

Build production JARs at manifest commits, each from its mod repository root:

```sh
# Storefront
./fabric/gradlew -p fabric build
# ItemSorter
./gradlew -p fabric build
```

Bundled libraries/web resources must stay private to each mod to avoid Fabric
classloader collisions. Image2Map URL-fetch commands require operator access.
Install Vanilla Tweaks' inner datapack ZIPs into `world/datapacks`, not the outer
bundle. Preserve configs and data for the pinned versions, not only JAR filenames.

### Optional resource pack and public routes

Katie Hardy's yellow/pink Hube paintings replace `minecraft:backyard` and
`minecraft:pond` (both 3×4), including existing placements; attribution stays in
`CREDITS.txt`. Rebuild from `hosts/newport/cheesetown/resource-pack`:

```sh
python -m zipfile -c ../downloads/cheesetown-paintings-1.0.1.zip pack.mcmeta assets CREDITS.txt
sha1sum ../downloads/cheesetown-paintings-1.0.1.zip
```

Update Compose's pack URL/version and SHA-1 together. Generated ZIPs stay in
ignored `downloads/`. The pack is optional; declining retains vanilla paintings.
Cheesetown terminates its own public TLS; preserve separate `/map`, `/storefront`
and `/item-sorter` routes and ordered slash/strip-prefix middleware. Public DNS
has its own dynamic apex record; game/DNS/forwarding readiness are distinct checks.

## Sven Co-op

The independent project is `hosts/newport/svencoop`, Compose name `svencoop`.
Archives/assets stay outside Git at `/mnt/terrabud/games/svencoop`; preserve whole
map packs and author configs, not only BSP files. Both `game` and `downloads`
track their existing `latest` images but deliberately disable Watchtower: update
by explicit pull/recreate after usage/backup checks.

Setup from the Infra root, using Newport's existing SOPS/age identity:

```sh
sops hosts/newport/svencoop/secrets/server.enc.yaml
(umask 077; ./scripts/render-secrets.sh newport/svencoop)
cd hosts/newport/svencoop
python3 install-maps.py ressya_no_tabi
sh -n entrypoint.sh
docker compose config --quiet
docker compose up -d
```

The parent `newport` render also includes this project. Encrypted server settings
own the password, FastDL origin and admin IDs. `.runtime-secrets/server.env` is
ignored private plaintext. Keep the dotenv-quoted `SVENCOOP_ADMINS` string with
escaped `\n` separators: the shared renderer does not add multiline quoting.
Passwords accept letters, numbers, dot, underscore and dash. The entrypoint writes
private configuration as the image's runtime user; do not weaken env-file modes
to give that user direct access. RCON stays disabled; cheats are admin-only.

`startup.cfg`/`mapcycle.txt` select `ressya_no_tabi`. Keep startup map names quoted:
engine direct `+map` parsing truncates hyphenated names. The Python 3.11+ installer
uses `maps.json` source URLs, SHA256 and archive prefixes, verifies cached/downloaded
archives, and rejects traversal/symlink entries. Investigate checksum mismatches;
do not change expected hashes just to install an unexpected download.

```sh
python3 install-maps.py ressya_no_tabi fail-mountain-20260531
docker compose ps -a
docker logs --tail 100 svencoop
```

Game is UDP 27015; FastDL is HTTP TCP 27015 and serves only `custom/` read-only.
Existing router forwarding is TCP/UDP 27015 to the server's configured LAN
address; preserve it unless explicitly asked to change it. A changing WAN IP may
require updating the encrypted FastDL origin independently of DNS. Inspect current
network/forwarding configuration rather than copying stale LAN addresses.

For an occupied server, install assets then issue `changelevel "BSP_NAME"` through
the Docker console input rather than recreating the process without warning.
Stop with `docker compose stop`; game uses SIGINT and a 30-second grace period.
Actual play readiness needs A2S queries and an external HTTP BSP/hash check, not
only valid Compose syntax.

Back up `/mnt/terrabud/games/svencoop` and the matching source/encrypted
configuration before replacing packs or images. No automated Sven backup schedule
is defined here. Do not promise recovery of an unfinished in-memory level/session;
coordinate a safe stopping point. Restore reviewed assets/configuration into an
empty destination with the game/download writer stopped, preserving the previous
set until play/FastDL checks pass.

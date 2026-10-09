# Fabric server configuration

Minecraft 26.2, Fabric Loader 0.19.5, launcher 1.1.2, Java 26.
The Compose server copies the external provisioned mods to `/data/mods` and
this directory to `/data/config`; runtime files remain writable. Configuration
sources win at boot.

Provision the ten upstream mods from pinned URLs and two reviewed custom builds:

```sh
uv run scripts/provision-cheesetown-mods.py --custom-dir /path/to/custom-builds
```

The default output is
`/mnt/terrabud/docker-data/newport/cheesetown/provisioned-mods`, mounted read-only
by Compose. Every JAR must match `../fabric-mods/runtime-manifest.json`; the
helper rejects in-repo output and unexpected JARs. A missing source mount fails
rather than silently creating an empty directory. Repeat provisioning to verify
existing files without replacing matching artifacts.

Build custom JARs from the manifest's exact commits, not moving branch tips:
From each repository root, Storefront uses `./fabric/gradlew -p fabric build`;
ItemSorter uses `./gradlew -p fabric build`. Copy only the full
production JARs into `--custom-dir`, never smoke/thin JARs. Rebuilds can differ
byte-for-byte; if a hash changes, review the artifact and manifest change
explicitly rather than bypassing verification. No JARs belong in Git.

The current live server still uses its old source mount. Provisioned files are
prepared for the reviewed Compose change; switching mounts requires a separate
service recreation after merge. Do not delete the old source files beforehand.

Server data: `/mnt/terrabud/docker-data/newport/cheesetown/fabric-data`.
The original `data` directory remains the stopped Paper rollback copy.
The scheduled backup service must follow the active `fabric-data` mount.

## Features

- Storefront and ItemSorter: maintained dual-platform builds from Storefront's
  `main` and the ItemSorter fork's default `master` branch. Exact source commits
  and artifact hashes are in `fabric-mods/runtime-manifest.json`. Keep each mod's
  bundled libraries and web resources private to avoid Fabric's shared classloader
  collisions. Do not install thin or smoke JARs.
- Distant Horizons 3.3.3: surface-only distant generation, centered on chunk 6,4
  with a 256-chunk radius. One worker at 25% duty; request distance 256 chunks,
  four generation requests/sec, eight load-sync requests/sec, 256 KiB/sec per
  player and 1024 KiB/sec globally. The fallback chunk mode is existing-only.
  Newly synthesized scenery omits trees and structures; this is not full world
  pre-generation. Managed updates are disabled. The client pack stays on 3.3.3.
- BlueMap: retained map IDs, render storage and all three dimension configurations;
  one render thread and the existing port 8100. Mojang assets remain accepted.
- Simple Voice Chat and AppleSkin: optional client enhancements. Voice uses UDP
  24454 and retains the prior group/recording policy.
- AudioPlayer replaces CustomDiscs: 16-block default disc range, 32-block maximum,
  10 MB uploads, one loader worker; web uploads and FFmpeg are disabled. Audio
  playback requires the optional Voice Chat client.
- Image2Map replaces ImageFrame: image commands require operator level 2, local
  file loading is disabled, image size capped at 512 pixels. No saved ImageFrame
  maps were found at migration. Do not grant image URL-fetch commands to ordinary
  players without reviewing network access and permissions.
- TakeASeat replaces GSit: empty-hand stair/slab sitting only, two-block maximum,
  obstruction and suffocation checks enabled. Reload is administrative.
- LuckPerms: YAML storage imported from Paper into `mods/luckperms/yaml-storage`.
  Vanilla operators and the whitelist remain unchanged. Obsolete Paper-specific
  permission nodes are inert; review new grants through LuckPerms.
- Lithium: server optimization. No hybrid Bukkit loader is installed.
- Vanilla Tweaks: More Mob Heads, Player Head Drops, Wandering Trades blocks-only.
  Only the three inner ZIPs belong in `world/datapacks`; provenance/hashes are
  retained in `fabric-mods/datapacks-manifest.json`.

Essentials, ProAntiTab, PacketEvents, DiscordSRV and InteractionVisualizer are
not loaded. Vanilla `/msg` remains; Essentials `/r` and its command-hiding policy
are not reproduced. The client pack is independent and was not changed here.

## Reviewed production baseline

Storefront PR #27 is merged into `main`; the ItemSorter fork's default `master`
branch contains the reviewed Paper/Fabric implementation. Production uses those
reviewed Fabric artifacts, not the smoke fixtures. The isolated Storefront
lifecycle/restart and ItemSorter filter/overflow/link/ratio/web tests passed,
as did the combined shipped-JAR HTTP/classloader regression. Real client clicks,
voice/disc playback and visual checks remain separate player-level checks.

Before this rollout, the stopped Fabric data and previous mods/config were
archived and tar-compared at:
`/mnt/terrabud/docker-data/newport/cheesetown/retirement-archives/fabric-reviewed-rollout-20261009T232053Z/`.
The archive has a SHA-256 sidecar. For an artifact-only rollback, stop Minecraft
and the backup writer, preserve any new progress, restore the two previous custom
JARs and runtime manifest from this archive's `fabric-mods/`, then restart and
verify. Do not restore the whole world merely to roll back JARs.

## Migration and rollback

Stopped-server backup (tar comparison and SHA-256 verified):
`/mnt/terrabud/docker-data/newport/cheesetown/retirement-archives/paper-to-fabric-20261007T021259Z/`.
This same-disk archive is rollback protection, not drive-failure protection.
It includes the old Compose/configuration and complete Paper data.

On the separate Fabric copy, move Paper's overworld `game_rules.dat`,
`scheduled_events.dat`, `wandering_trader.dat`, `weather.dat`, and
`world_gen_settings.dat` into `world/data/minecraft/`, following current Paper
migration docs. Keep dimension directories and `world/players` intact.
Storefront's database/config is copied into `config/storefront`. The stopped
world scan found no ItemSorter filters, so no legacy-book conversion was needed.

The sole CustomDiscs item at chest 100,72,74 slot 17 retains its original metadata
and now points to AudioPlayer UUID `60e54a86-64e7-47d9-b119-51e6a2944cf5`, range 16.
Its imported MP3 and metadata live in `world/audio_player_data` and are backed up
with the world. Keep the old MP3/plugin data for rollback.

For a rollback, first stop Fabric cleanly and archive its new progress separately.
Restore `compose.yml` from this archive's `infra/compose.yml` into the current
Cheesetown stack directory, then recreate Minecraft, backup and the frontend with
`docker compose -f hosts/newport/cheesetown/compose.yml up -d --no-deps --no-build --pull never --force-recreate minecraft backup storefront`.
The restored Compose points to the untouched original Paper `data` directory and
retained Paper configuration. Returning this way discards subsequent Fabric
progress; do not silently merge worlds or boot Paper against the modified Fabric
copy. Verify player state and public endpoints after any rollback.

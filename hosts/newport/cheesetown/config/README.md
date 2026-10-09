# Retained Paper configuration

The active server uses `../fabric-config/`; this directory is for Paper rollback.

itzg copies this read-only `/plugins` mount into writable `/data/plugins`.
Copying configuration does not remove old runtime files. Keep plugin versions
pinned in `../plugins.txt` and review new options when upgrading.

## Settings

- TeaksTweaks: mob heads, player heads, and wandering-trader mini-blocks only.
  Crafting tweaks, trader player heads, update checks, and log sharing are off.
- GSit: empty-hand block sitting within three blocks; stacking/crawling gestures
  are off. Permissions below are required to prevent command-based poses.
- Voice Chat: optional clients, UDP 24454 at `cheesetown.rocks`; groups,
  recording, and spectator interactions are off.
- BlueMap: one render thread, metrics off, Mojang assets accepted; listener 8100.
  Expose it through the existing map route rather than directly to the WAN.
- CustomDiscs: discs only, 16-block default/32-block maximum range, 10 MB limit,
  80-character filename limit. Ordinary textures; horns/player heads are off.
- ImageFrame: five maps/player, size 16, 5 MiB limit, 15-second processing limit,
  one task and ten packets/tick. Require empty maps outside creative. Only the
  configured HTTPS Imgur/Discord/Mojang origins are allowed; uploads and
  invisible-frame conversion are off.
- EvenMoreFish is retired; its provisioning and default-group grants were removed.
- DHSupport: source-built `0.15.0-SNAPSHOT` at commit
  `04fc2e17f9c04e717a1e09997c3201ac5bab9e53` from
  `https://gitlab.com/distant-horizons-team/distant-horizons-server-plugin`.
  Build with JDK 21 and `./gradlew clean build`; use the shaded
  `build/libs/1.16.5/` artifact. SHA-256:
  `05ac05bc55904c469a93e16b0d5e78cea54d51829af5dbc0692967f12b9e93a9`.
  It uses protocol 16 with DH 3.3.3. For Paper rollback only, provision the JAR
  outside Git and mount it explicitly; this checkout does not supply it.
  `DHSupport/config.yml` bounds existing-terrain LODs. Restore old cache data
  with its matching plugin when undoing a schema migration.
- DiscordSRV: unconfigured. Keep console execution, linking, and role/nickname/
  ban sync disabled. A blank-token warning does not mean a connected bot.
- AppleSkinSpigot: optional client HUD synchronization; no config directory.

## Permissions and dependencies

CustomDiscs needs both Voice Chat and PacketEvents; check `paper-plugin.yml`,
not just `plugin.yml`. Keep disc downloads administrator-only: this plugin has
no URL allowlist, and file-size caps do not restrict network access.

For sitting-only players, deny `GSit.*`, `GSit.Pose.*`, `GSit.Crawl.*`,
`GSit.Lay`, `GSit.LayBack`, `GSit.BellyFlop`, `GSit.Spin`, `GSit.Crawl`,
`GSit.CrawlSneak`, and `GSit.CrawlToggle`. Retain `GSit.Sit`, `GSit.SitClick`,
and `GSit.SitToggle`. Root/category wildcards override leaf-only denials.
`CommandBlacklist` and `default-crawl-mode=false` do not disable pose commands.
Apply the same restrictions to operators if they are subject to this policy.

Keep ImageFrame creation/overlay/refresh administrator-only. Deny
`imageframe.create.animated` for a still-image policy; there is no global
animation-disable key. Do not grant unlimited-map or admin bypass permissions
to ordinary players. URL restrictions are plugin policy, not a verified SSRF
boundary.

Test plain-client joins, two-client voice, non-operator permissions (including
namespaced commands), map limits, and backup/restore before deploying changes.
Static config checks cannot establish those behaviors. These are Paper settings;
do not use this directory as Fabric configuration.

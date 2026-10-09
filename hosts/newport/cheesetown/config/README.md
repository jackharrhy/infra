# Paper configuration

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
- EvenMoreFish: common catches with ordinary rods/textures; no economy/database,
  hunting, lava/void fishing, or bait catch chance. Daily ten-minute contest at
  18:00 needs two players and awards messages only. Empty `_disabled.txt`
  directories stop bundled baits/rods from regenerating; absent directories do not.
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

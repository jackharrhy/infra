# cheesetown plugin baseline

These directories are copied from the read-only `/plugins` provisioning mount into
writable `/data/plugins` by itzg. This is a **fresh-data baseline**, not a cleanup
migration: copying does not delete old EMF rarities, competitions, baits or rods.
Keep the exact pinned JARs below; review newly introduced options before upgrades.
No client resource pack is requested or required by these configurations.

## Choices

- **TeaksTweaks/config.yml:** full 2.1.4 defaults with only `more-mob-heads`,
  `player-head-drops`, and `wandering-trades` enabled. All 78 packs are explicitly
  covered; all 42 crafting tweaks are disabled. Trader mini-blocks retain four
  trades/eight items; trader player heads and stonecutter mini-block crafting stay
  disabled. Update checks, mechanics command and log-paste sharing are disabled.
- **GSit/config.yml:** full 3.5.1 defaults; empty-hand block sitting within three
  blocks remains enabled. Player/NPC stacking and double-sneak crawling are off.
  Lying does not reset phantom timers or contribute to night skipping. See the
  mandatory permission restrictions below: this config alone cannot disable poses.
- **voicechat/voicechat-server.properties:** UDP `0.0.0.0:24454`,
  advertised as `cheesetown.rocks:24454`, `force_voice_chat=false`. Proximity voice only: groups, built-in recording, and
  spectator interactions are off. Clients without the mod can join normally.
- **BlueMap/core.conf, webserver.conf:** Mojang asset download accepted, one render
  thread, metrics off; internal web listener `0.0.0.0:8100`. Do not publish 8100
  directly to the WAN. BlueMap generates its normal world maps/webapp/storage
  configuration. Short configs use the tagged Java config-class defaults.
- **CustomDiscs/config.yml:** music discs enabled, 16-block default / 32-block max
  range; downloads capped at 10 MB and filenames at 80 characters. Download and
  creation permissions remain upstream operator-only. Custom horns and audio
  player heads are disabled, as unapproved extra features. The horn cooldown is
  explicitly 200 ticks if horns are enabled later; no disc cooldown key exists in
  this version. Custom model data is disabled; ordinary item textures remain.
  This plugin has no URL allowlist setting: keep downloads administrator-only.
- **ImageFrame/config.yml:** five image maps per ordinary player, max image-map
  size 16, 5 MiB file cap, 15-second processing cap, one concurrent task and ten
  map packets/tick. Empty maps are required outside creative. URLs are restricted
  to the listed HTTPS Imgur, Discord and Mojang texture origins. The embedded
  upload server, optional ImageFrame client integration and invisible-frame
  conversion are disabled. Permissions can bypass creation limits; see below.
- **EvenMoreFish/config.yml:** fishing and catches enabled using vanilla rods;
  all economy providers and database disabled, no Vault required. Hunting, lava
  and void fishing remain off. Bait catch chance is zero.
  `rarities/common.yml` keeps 23 upstream common catches with normal item textures;
  the pufferfish catch effect is removed. No other rarities are provisioned.
  `competitions/main.yml` provides one ten-minute largest-fish contest daily at
  18:00 server time, minimum two players, with congratulatory messages only—no
  free diamonds, XP, economy payments or console commands.
  `baits/_disabled.txt` and `rods/_disabled.txt` deliberately retain empty folders.
  In 2.4.6 `AbstractFileBasedManager` generates bundled defaults only if a folder
  is absent; its `FileUtil` skips underscore-prefixed entries. The same existing-
  directory rule prevents extra bundled rarities and weekend competitions.
- **DiscordSRV/config.yml, linking.yml, synchronization.yml:** blank bot token and
  channels; console channel and chat-channel console commands disabled. Console
  commands also use an empty allowlist. No required account linking, role sync,
  nickname sync or ban sync. Bot setup is deferred. Blank-token startup may log a
  configuration warning; this is deliberately inert, not a connected Discord bot.
- **AppleSkinSpigot:** verified 2.0.2 JAR has no config resource and needs no config
  directory. It only syncs data for optional client HUD use.

## Mandatory deployment follow-up (outside this directory)

1. **CustomDiscs 6.0.3 requires `voicechat` AND `packetevents`.** Both are hard
   `dependencies.server` entries in `paper-plugin.yml`; `plugin.yml` alone omits
   them. Provision a compatible, pinned PacketEvents JAR before startup. All
   other inspected JARs declare no hard plugin dependency; EMF's Vault is soft.
2. **GSit command permissions must be denied separately.** Deny `GSit.*`,
   `GSit.Pose.*`, `GSit.Crawl.*`, `GSit.Lay`, `GSit.LayBack`, `GSit.BellyFlop`,
   `GSit.Spin`, `GSit.Crawl`, `GSit.CrawlSneak`, and `GSit.CrawlToggle` for players
   subject to the sitting-only policy. Explicitly retain `GSit.Sit`,
   `GSit.SitClick` and `GSit.SitToggle`. Apply denials to operators too if the
   policy must include them. `PermissionService` ORs leaf, category and root
   wildcard grants, so leaf-only denials are insufficient when wildcards remain.
   `Options.CommandBlacklist` only blocks commands while using a feature; it is
   NOT a command-registration disable list. `default-crawl-mode=false` disables
   the gesture default, NOT `/crawl`.
3. **ImageFrame URL fetching remains administrator-only:** retain the upstream
   operator-only creation, overlay and refresh permissions; do not grant URL-fetch
   commands to ordinary players. Deny `imageframe.create.animated`, including for
   operators if still-image-only is strict. Do not grant
   `imageframe.createlimit.unlimited` or administrative bypass permissions to
   ordinary players. Strict limits also require restricting operator privileges.
   No global animation-disable config key was found in the pinned JAR.
4. Keep CustomDiscs download permission restricted to trusted administrators;
   file-size limits are not network egress controls. ImageFrame's URL restrictions
   are plugin policy, not an independently verified SSRF boundary.
5. Verify clean startup on the pinned Paper version, plain-client join, two-client
   voice, permissions (including namespaced command aliases), image/map limits,
   BlueMap rendering, EMF catches/contest and inert Discord configuration before
   calling deployment complete. No server, Docker or gameplay test was run here.

## Provenance and static verification

Retrieved the actual pinned upstream JARs below in memory and inspected
`plugin.yml` plus `paper-plugin.yml` where present. YAML configurations preserve
full comment-stripped defaults unless explicitly documented above. Every emitted
YAML key was checked against its exact JAR resource; all emitted YAML parsed and
passed the write tool's YAML lint. Properties keys and data-folder filename were
verified from the voicechat 2.6.23 class constant pools, including ConfigBuilder's
missing-value/default handling. These are static checks, not runtime validation.

Additional tagged source inspected:
- [GSit 3.5.1](https://github.com/gecolay/GSit/tree/3.5.1): ConfigService,
  PermissionService, GCrawlCommand.
- [BlueMap v5.24](https://github.com/BlueMap-Minecraft/BlueMap/tree/v5.24):
  CoreConfig, WebserverConfig and Paper BukkitPlugin.getConfigFolder.
- [EvenMoreFish v2.4.6](https://github.com/EvenMoreFish/EvenMoreFish/tree/v2.4.6):
  ConfigBase, AbstractFileBasedManager, FileUtil, FishManager and CompetitionFile.

| Plugin name / data folder | JAR version | Upstream artifact | SHA-256 |
| --- | --- | --- | --- |
| BlueMap | 5.24 | [bluemap-5.24-paper.jar](https://cdn.modrinth.com/data/swbUV1cr/versions/zjZDXCw6/bluemap-5.24-paper.jar) | `23592af35d1289ff9251301994948f1d69e8d81b569515ce81a91cba4daabc78` |
| GSit | 3.5.1 | [GSit-3.5.1.jar](https://cdn.modrinth.com/data/GOHbQGyX/versions/nZM8fxpG/GSit-3.5.1.jar) | `b0749412b65c01bdcd683820a764a2f769ac557eb0b691856d267a63f283ca1c` |
| TeaksTweaks | 2.1.4 | [teakstweaks-2.1.4.jar](https://cdn.modrinth.com/data/Xdn5t532/versions/ReH3FreP/teakstweaks-2.1.4.jar) | `efcc06cd9636dc82019d0d3c5ce0b87187a87bf5e87a074fb5219c7da2b79978` |
| ImageFrame | 2026.1.4.0 | [ImageFrame-2026.1.4.0.jar](https://cdn.modrinth.com/data/lJFOpcEj/versions/nt0GWT1y/ImageFrame-2026.1.4.0.jar) | `193dc95276472411e5c144e089a0e64015658df4b2bab867b0b4f1179bc577a6` |
| EvenMoreFish | 2.4.6 | [EvenMoreFish-2.4.6.jar](https://cdn.modrinth.com/data/vlh7rLCf/versions/KEn7lPL0/EvenMoreFish-2.4.6.jar) | `5c275655d7dde68abe60d3dbb1c2f65dc49b133d4e90c2ce34e87e1efd30f064` |
| voicechat | 2.6.23 | [voicechat-bukkit-2.6.23.jar](https://cdn.modrinth.com/data/9eGKb6K1/versions/IhqyykOv/voicechat-bukkit-2.6.23.jar) | `fd0d67f9daa07ac5769d2ebc9d16b6f0e8b603aea98a60605335dfc8e5148164` |
| DiscordSRV | 1.30.5 | [DiscordSRV-Build-1.30.5.jar](https://cdn.modrinth.com/data/UmLGoGij/versions/ATlquwiT/DiscordSRV-Build-1.30.5.jar) | `ef2fa1f2eb146c7c77412b7190a7dd33f1fc91282683fe45407739554c8aefef` |
| CustomDiscs | 6.0.3 | [custom-discs-6.0.3.jar](https://cdn.modrinth.com/data/b7pWaVta/versions/8p8QKPwN/custom-discs-6.0.3.jar) | `14e0205833cd88373dffc70cf12ca7039214deec84b19b8414616e963a229ae6` |
| AppleSkinSpigot | 2.0.2 | [AppleSkinSpigot-2.0.2.jar](https://github.com/Siebrenvde/AppleSkinSpigot/releases/download/2.0.2/AppleSkinSpigot-2.0.2.jar) | `f2f601c120ee266ba7df8b374371d910512cf66e358d0e9ba8cacaf7095077fa` |

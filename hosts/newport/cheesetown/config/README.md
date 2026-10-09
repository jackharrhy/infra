# Retained Paper configuration

The active server uses `../fabric-config/`; this directory is for Paper rollback.

itzg copies this read-only `/plugins` mount into writable `/data/plugins`.
Copying configuration does not remove old runtime files. Keep plugin versions
pinned in `../plugins.txt` and review new options when upgrading.

## Paper DHSupport build

Source-built `0.15.0-SNAPSHOT` at commit
`04fc2e17f9c04e717a1e09997c3201ac5bab9e53` from
`https://gitlab.com/distant-horizons-team/distant-horizons-server-plugin`.
Build with JDK 21 and `./gradlew clean build`; use the shaded
`build/libs/1.16.5/` artifact. SHA-256:
`05ac05bc55904c469a93e16b0d5e78cea54d51829af5dbc0692967f12b9e93a9`.
It uses protocol 16 with DH 3.3.3. For Paper rollback only, provision the JAR
outside Git and mount it explicitly; this checkout does not supply it.
`DHSupport/config.yml` bounds existing-terrain LODs. Restore old cache data
with its matching plugin when undoing a schema migration.

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

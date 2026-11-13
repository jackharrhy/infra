---
name: infra-games
description: "Use when operating game servers and client packs."
---

# Game service operations

Read [games](../../../docs/games.md), the exact nested project's manifest and
[fleet operations](../infra-host-maintenance/SKILL.md). Newport's game projects are
not the main host stack. Permission for a scoped restart is not permission for a
world conversion, modpack replacement, map deletion or new network exposure.

## Check the live session

1. Identify actual map/world, players, version/mods, persistence and updater policy.
   Use native status/RCON/protocol interfaces without printing join passwords,
   RCON secrets, admin identity lists or unrelated player data.
2. Warn/save when appropriate and choose a bounded safe stopping point. Do not
   wait indefinitely for an empty Minecraft server; do not claim historical rows
   or a settled shot preserve an unfinished in-memory human game.
3. Preserve a suitable recoverable world/config/image set. Native version/world
   conversions need genuine recovery checks; routine maintenance is not a reason
   to export the whole server again. Failed backups must not trigger pruning.
4. Operate only the selected project/service and verify reconnect, actual map,
   mod behavior and the affected public asset/protocol path. A2S or HTTP readiness
   is not proof that a real player joined or a world conversion succeeded.

## Avoid destructive administration shortcuts

- Keep complete map packs and author configs; a BSP alone is not a pack. For
  authorized removal, subtract retained packs' shared assets and update startup
  plus mapcycle together. Reject unsafe archive paths/checksum surprises.
- For occupied Sven Co-op, use a bounded console attachment that closes only its
  socket. A timeout-killed signal-proxying attach client can signal the server.
  Read back mounted file bytes after atomic host edits; a file bind may retain an
  old inode. Verify/reapply cosmetic settings after changelevel, not before it.
- Resolve admin access from verified native identity. Admin-only cheats, global
  CVARs, RCON and owner privileges are separate capabilities.
- Optional launcher packs do not upgrade running servers or existing launcher/JVM
  components. Verify indexed and served artifacts; keep pack publishing, server
  provisioning and world maintenance separate.
- Tar's changed-during-read status is not a clean backup. Protect first/current
  recovery and designated milestones; same-drive archives/hardlinks do not provide
  drive-failure recovery. Use the existing retention helper, not broad globs.

Application/plugin development belongs in its owning repository. Retain game
credentials, player bindings, private inventories and transient rollout receipts
outside this public guidance.

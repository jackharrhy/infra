# Working in infra

Read README.md for the fleet CLI, host layout, routing and secret-rendering commands.
Use the primary ~/infra checkout and coordinate one source/index writer; do not
introduce worktrees to avoid coordinating. Preserve unrelated work and live routes.

## Maintenance defaults

- Prefer current, working services over indefinite freezes. When asked to maintain,
  update or deploy a service, carry ordinary scoped maintenance through to completion;
  brief downtime is acceptable. Do not ask again for each routine restart.
- Keep first-party apps on their actual main-published tracking tag (`main` or
  `latest`). Use immutable pins for a concrete temporary rollout need, not as the
  default finish state. Keep intentional vendor versions and real security holds.
- Watchtower should work. If you pause it, exclude an app or pin an image temporarily,
  remove that temporary restriction and verify updates are operational before
  finishing. If a real blocker remains, narrow the hold and state its owner,
  release condition and next action; never silently leave the fleet frozen.
- Check actual usage, then act proportionately. Ordinary website traffic is not a
  veto on maintenance. For Minecraft, warn connected players, save/backup as needed,
  restart gracefully and verify return; do not wait indefinitely for zero players.
- Brief interruption is not permission to lose data. Drain unrecoverable in-memory
  games/jobs or use a tested recovery path. Automatic updates need the same protection.
- Match checks to the change. Routine image/config refreshes need focused readiness
  and persistence checks, not a repeat of every historical migration test. Auth,
  schema, provider and world migrations need their relevant cutover checks; unrelated
  optional coverage must not become a fleet-wide deployment gate.
- Ask for materially destructive or expanded scope, not routine substeps already
  covered by the request. An inspection/planning question is not a deployment request.
  Preserve the first legacy backup and a current recovery point; no broad Docker
  pruning, database resets, world conversions or credential retirement by implication.

## Task guidance

- Fleet operations and Watchtower: load [infra-host-maintenance](.agents/skills/infra-host-maintenance/SKILL.md).
- Host storage, packages and remote access: load [host-system-maintenance](.agents/skills/host-system-maintenance/SKILL.md).
- Application access, recovery and media: load [infra-services](.agents/skills/infra-services/SKILL.md).
- Game servers, backups and optional packs: load [infra-games](.agents/skills/infra-games/SKILL.md).
- Shared handoffs: read [agent operation](docs/agent-operations.md); keep one owner per cutover.

Keep this file short and forward-facing. Procedures belong in skills; current
holds, receipts and project-specific acceptance status belong in the active task.

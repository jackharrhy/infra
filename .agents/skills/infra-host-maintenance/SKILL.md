---
name: infra-host-maintenance
description: "Use when maintaining Newport and Mug services."
---

# Fleet operations

Use this repository's CLI and current manifests. Skills describe procedure, not
permission: inspection does not authorize deployment or change the active owner.
Coordinate one source/index/runtime writer. Do not reset another task's work,
introduce worktrees, or copy an entire live configuration to avoid coordination.

## Read first

- [README](../../../README.md): CLI, host layout and documentation map.
- [Operations](../../../docs/operations.md): scope, routing, SOPS, DNS and NAS.
- [Applications](../../../docs/applications.md): identity and application recovery.
- [Media](../../../docs/media.md) or [games](../../../docs/games.md) for that target.
- [Agent operation](../../../docs/agent-operations.md): public/private context and
  explicit ownership transfer.

Inspect actual live settings before acting; source, registry publication, running
image, readiness and authenticated acceptance are different evidence.

## Routine workflow

1. Resolve the target, actual Compose project and current source/runtime owner.
   Fetch origin before Git comparisons; preserve unrelated WIP and watched files.
   `uv run cli.py status HOST` compares Git, not health.
2. Inspect running image ID and OCI revision, mounts, environment privately, live
   use and free space. Compare with the intended settings. Environment order is
   irrelevant; changed values are not. Do not print raw env/labels or credentials.
3. Choose proportional recovery. A compatible image/config change normally needs
   an available prior immutable image and adequate existing recovery, not a fresh
   tar export/database copy/full migration matrix. Schema/destructive changes need
   their real consistency and downgrade checks. Preserve first/current recovery.
4. Run the authorized service-scoped operation. For example:

   ```sh
   uv run cli.py refresh newport --service steve
   uv run cli.py refresh mug --service radio-celld --service teacms
   ```

   Repeated `--service` is explicit scope. Unscoped refresh changes siblings and
   prunes images. Nested game projects and `pull_policy: never` builds have their
   own procedures. Manual Compose does not execute Watchtower's drain/backup hooks.
5. Verify the selected image, restart/OOM state, real protocol response and affected
   persistence/user path. If the intended image is already healthy, avoid a second
   restart. A protected redirect/401 is not a successful authenticated workflow.
6. Restore normal tracking and updater scope. A remaining per-service hold must
   have an owner, concrete blocker, release condition and next action. Read back
   the exact changed external target before reporting completion.

## Safety boundaries that change execution

- Ordinary website traffic can tolerate brief maintenance. Warn/save Minecraft
  players. Drain genuinely unrecoverable games/jobs with an admission gate, not
  merely an idle snapshot. Do not wait indefinitely for an empty ordinary service.
- Keep first-party images on their actual main-published moving tags after a
  temporary rollout pin. Preserve deliberate vendor versions and security holds.
  Newport's opt-in updater policy is not Mug's policy; inspect each actual updater.
- A Docker daemon restart can leave a long-lived socket consumer on an obsolete
  inode. Compare source/mounted socket identity before claiming discovery works.
- Do not hand-edit rendered secrets or apply unrelated env drift during an image
  refresh. Use the normal SOPS renderer and private modes. Keep encryption/auth
  keys with recoverable state; a database alone may be insufficient.
- SQLite recovery requires the stopped owner's complete current main/WAL/SHM set
  preserved aside and an empty restore destination. An image rollback does not
  justify erasing newer authorization decisions or application writes.
- Pull/replace one scoped service at a time on a small root filesystem. Docker
  cleanup, volume deletion, backup deletion and world conversion are separate
  scopes; never infer them from a container-removal or update request.
- Inspect publisher fan-out before a release with real runtime consequences. A
  monorepo source move does not change provider/data/authorization ownership.
  Issuer grants, native accounts, native roles and existing sessions are distinct.

Keep current holds and receipts in the private task record, not an append-only
public skill. Put reusable improvements in the existing cohesive documentation.

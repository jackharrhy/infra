---
name: infra-services
description: "Use when operating application services."
---

# Application operations

Load [fleet operations](../infra-host-maintenance/SKILL.md), then the target's
[application procedure](../../../docs/applications.md) and current manifest.
For Jellyfin, Rotund and the media pipeline, use
[media operations](../infra-media/SKILL.md). Source owners implement applications;
the shared runtime operator owns an explicitly selected deployment boundary.

## Inspect the actual contract

- Separate source, publisher artifact, selected runtime and user-path acceptance.
  Read the actual listener, healthcheck and authentication contract. Do not convert
  a correct login redirect into an imagined anonymous-200 requirement.
- Keep issuer eligibility, native accounts/roles, browser proxy sessions and API
  credentials separate. Names/emails are not immutable identity or authorization.
  Removing an issuer grant does not prove native session/token revocation.
- Preserve exact app-only service credentials and the reviewed actor/capability
  boundary. Do not broaden a fixed single-account mapping into multi-user access.
- State, settings, uploads and matching keys are recoverable sets; logs/caches are
  not authorization databases. Source consolidation is not runtime/data migration.

## Operate proportionately

1. Confirm the one runtime writer, mounts, effective settings and a suitable
   recovery point. Compare live inputs privately before applying rendered config.
2. Use the repository's scoped CLI or documented local-image build path. Keep
   automatic-update backup hooks effective; manual Compose needs its gates run
   explicitly. Restore temporary rollout restrictions when their reason clears.
3. Verify the actual affected path and persistence. A login redirect or enabled
   setting is not successful sign-in/playback/import. Avoid reopening unrelated
   migration acceptance for a routine compatible patch.

## Application state boundaries

Private vault synchronization is not public writing/asset publication. Keep one
sync writer, matching private configuration recovery and reviewed public exports.
Media storage, native account/client boundaries and acquisition/cleanup workflows
are owned by the [media skill](../infra-media/SKILL.md) and its guide.

Keep product-specific implementation details in their repositories. Public Infra
guides must not contain credentials, private content, sensitive identity bindings
or historical acceptance reports presented as current guarantees.

# Repository-owned GitHub Actions

Keep complete workflows in each application. This directory holds recipes and
maintenance notes, not workflows that applications call at run time. Copies become
ordinary project-owned files: adapt them, review changes, and never overwrite them
from a template. A fork must not need this repository to build.

## First pilot: 8mb

Source: https://github.com/jackharrhy/8mb
Deployment: `hosts/mug/compose.yml`, `ghcr.io/jackharrhy/8mb:main`.

Its `.github/workflows/build.yml` checks workflow syntax/security, runs Node 24
unit tests and the TypeScript/Vite build, builds a disposable production container,
and runs the existing Chromium/media/edge/timeline checks against localhost.
Only a push to main can publish, after all checks pass. The public image retains
`:main` and the commit-SHA tag. No central workflow or private token is required.
The implementation lives in 8mb; this record is not a generated source of truth.

## Recipes

- [Workflow lint](recipes/workflow-lint.yml): copy into `.github/workflows/`.
- [Dependabot](recipes/dependabot.yml): merge into `.github/dependabot.yml`; do not
  replace existing ecosystems or custom update rules.

The lint recipe is also the `workflows` job in 8mb's combined CI. Do not install
both forms. jactionlint uses its default profile with warnings treated as failures;
there is no blanket ignore file or findings baseline. Shellcheck is required so
shell-script checks cannot silently disappear. `uv` runs the pinned PyPI release
without adding application dependencies. Review the jactionlint pin explicitly:
Dependabot updates action references, not version strings in arbitrary shell code.

## Standard

- Pin actions to verified release commits, with version comments for update bots.
- Use supported runtimes matching the application/Dockerfile, explicit job
  timeouts, and concurrency appropriate to publishing. Do not cancel an in-flight
  publication to start another one.
- Default to no token permissions. Checkouts do not persist credentials. PR jobs
  get no package-publishing permissions or registry login; do not use
  `pull_request_target` to execute contributor code.
- Publish only from the intended trusted branch/release event after tests pass.
  Preserve deployed registry names and tags: Watchtower may follow them.
- A publishing job builds from source without restoring build/tool caches.
  Read-only test jobs may use caches. Include OCI source/revision labels, build
  provenance/SBOM and a digest-bound attestation when publishing supports them.
- Keep project tests, fixtures and reproduction commands in the project. Never
  point CI browser tests at production or a developer's tailnet preview.
- Keep Actions updates scheduled and reviewable. Group minor/patch updates;
  review major changes separately. No fleet-wide automatic merging.

## Applying a change to the group

1. Start with deployed first-party services in `hosts/*/compose.yml`, including
   nested stacks. Resolve the actual source repository from image labels or project
   documentation: an image name is not always a repository, and one repo may build
   several images. Record public/private ownership rather than assuming it.
2. Fetch each repository, inspect its instructions, workflows, required checks and
   dirty state. Use an isolated branch/worktree; preserve unrelated changes.
3. Audit before editing. From the target checkout, with uv and shellcheck installed:

   ```sh
   uvx --from jactionlint==2.3.0 jactionlint --online --strict-exit
   ```

   Without shellcheck on PATH, use
   `mise exec shellcheck@0.11.0 -- uvx --from jactionlint==2.3.0 jactionlint --online --strict-exit`.
   Online checks use the developer's existing GitHub authentication. Do not copy
   credentials into workflows or this directory.
4. Apply a small policy/version change to selected repositories, adapting to their
   current files. Use these recipes as examples, not replacement generators. Read
   major-version release notes and verify tag-to-commit resolution.
5. Run lint, application checks and container/browser checks. Open a per-repository
   PR with results and publishing/tag implications. Keep required-check names in
   mind; changing branch protection is a separate decision.
6. Do not merge or refresh production as a side effect of maintenance. A merge may
   publish an image that Watchtower deploys automatically.

No generator, updater service or audit framework is needed for the first pilot.
Add a targeted migration only when a repeated change makes it worth maintaining.

## References

- [jactionlint CI](https://jactionlint.jdx.dev/ci)
- [Dependabot Actions updates](https://docs.github.com/en/code-security/dependabot/working-with-dependabot/keeping-your-actions-up-to-date-with-dependabot)
- [Riley's workflows](https://github.com/nint8835/workflows): useful implementation
  examples; our applications intentionally do not depend on a central workflow.

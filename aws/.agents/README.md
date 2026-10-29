# Official AWS and Pulumi skills

Project-local copies from the vendor-maintained repositories:

- https://github.com/aws/agent-toolkit-for-aws
- https://github.com/pulumi/agent-skills

Only five relevant skills are installed, including their supporting references.
Their contents are unmodified. `skills.lock.json` records each upstream commit,
source path, and SHA-256 hash. Vendor licenses are in `upstream-licenses/`.

These are instruction files, not running services. No MCP server, cloud product,
subscription, credentials, or infrastructure is configured by this installation.
They support the existing AWS CLI and Pulumi workflow; no Pulumi Cloud migration
is required. The security skill is read-only; implementation uses the relevant
IAM/Pulumi guidance and the user's authorized scope.

Work from `~/infra/aws` so the project-local skills are discoverable. A session
already running elsewhere may need a new turn/session in that directory.

Before the account migration, check upstream for newer revisions and consult live
AWS/Pulumi documentation. To refresh, use skill-installer with a selected commit
and temporary destination, review the changes, replace the selected skill folders,
and update the recorded hashes and licenses. Avoid silently following `main` or
installing unrelated migration, delegation, CDK, or application-authentication
bundles.

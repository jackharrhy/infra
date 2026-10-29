# AWS infrastructure

Use the official project-local skills in `.agents/skills` when relevant:

- `aws-iam`: IAM, role trust, STS, and Organizations policy details.
- `aws-security`: read-only security-service assessment and recommendations.
- `aws-billing-and-cost-management`: pricing, budgets, and cost analysis.
- `pulumi-best-practices`: Pulumi authoring, dependencies, secrets, and aliases.
- `provider-upgrade`: provider upgrades with a reviewed, explained preview.

Upstream revisions, file hashes, and licenses are recorded under `.agents/`.
Read only the relevant skill and references. Check current vendor documentation
for API details, supported versions, and prices; pinned skills can become stale.
Skills are guidance, not permission to execute every example or enable services.

Keep account/access setup, mail infrastructure, and insta-game ownership distinct.
Pulumi must not adopt resources also managed by insta-game's Go CLI/CloudFormation.
Check the explicit AWS profile, STS account identity, and region before mutations.
Preview and review intended changes before applying. Preserve resource identities
when refactoring; use aliases/imports rather than accidental replacement.

The existing project uses local `.pulumi` state and `.env` for its passphrase.
Preserve both and make a recoverable backup before state or account migration.
Do not print credentials or decrypted secrets, or commit state, `.env`, or exports.

Account/access separation should add no recurring service cost. Identify additional
costs before enabling optional services or duplicating workloads for migration.
Jack has separately authorized the account/mail migration. Cross-account resources
will be recreated: preserve function, data, recovery, and least privilege rather
than treating old IDs as a permanent migration veto. Recovery emails must come
from Jack. Review previews before applies and coordinate Auth SMTP cutover.
Installing skills by itself does not authorize an apply.

# AWS and Pulumi skills

`skills-lock.json` pins five skills from `aws/agent-toolkit-for-aws` and
`pulumi/agent-skills`: IAM, security assessment, billing, Pulumi best practices,
and provider upgrades. It uses the skills CLI native version-1 format, including
commit refs, source paths and folder hashes. Third-party files stay local.

From `aws/`, restore with the skills CLI (verified with version 1.7.4):

```sh
DISABLE_TELEMETRY=1 DO_NOT_TRACK=1 skills experimental_install
```

If the CLI is not installed, use the same version without a global installation:

```sh
DISABLE_TELEMETRY=1 DO_NOT_TRACK=1 npx --yes skills@1.7.4 experimental_install
```

Run from this directory, not HOME. The CLI restores `.agents/skills/`; local
skills and agent links are ignored. Review any lock changes when refreshing
upstream refs. Consult current vendor documentation before cloud changes.
Restoring instruction files does not configure services or authorize an apply.

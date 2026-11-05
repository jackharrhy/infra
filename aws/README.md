# AWS

Pulumi manages accounts and mail in `us-east-1`:

| Directory     | Project / stack              | Owns                                                                                   |
| ------------- | ---------------------------- | -------------------------------------------------------------------------------------- |
| `foundation/` | `jack-foundation/management` | Protected production/sandbox accounts and Jack's Identity Center access                |
| `mail/`       | `jack-mail/production`       | Production SES, SNS, inbound S3 → Lambda → SQS, campaign media and machine credentials |

Lists runs on Mug with its SQLite database. Insta-game's Go CLI/CloudFormation
owns game infrastructure separately. Each Pulumi project has its own state in
the local backend.

## Commands

From `aws/`, install dependencies and load the backend:

```sh
pnpm install --frozen-lockfile
set -a
. /home/jack/infra/aws/.env
set +a
export PULUMI_BACKEND_URL=file:///home/jack/infra/aws
export AWS_CONFIG_FILE=/home/jack/infra/aws/.runtime-secrets/aws-config
```

Choose the project directory and stack before running Pulumi:

```sh
cd foundation
aws sts get-caller-identity --profile jack-admin
pnpm run check
~/.pulumi/bin/pulumi preview --stack management --diff
```

Review the preview before `pulumi up --stack management`. Member accounts are
protected and `closeOnDeletion` is false. The foundation imports the existing
`JackAdministratorAccess` permission set, preserving its twelve-hour sessions,
AdministratorAccess attachment and management assignment.

Configure each stack with an explicit AWS profile, `us-east-1`, and
`aws:allowedAccountIds` containing only its target account ID as a string
(use `pulumi config set --path 'aws:allowedAccountIds[0]' --type string ID`):

- Foundation uses `jack-admin`, `managementAccountId`, `ssoInstanceArn`,
  `ownerUserId`, `ownerPermissionSetArn`, and secret `productionEmail` and
  `sandboxEmail` values. Local `Pulumi.management.yaml` is ignored.
- Mail uses `jack-prod`, `accountId`, and `receiveEnabled` (true for live inbound mail). Initialize its stack with `pulumi stack init production`.

Owner profiles use Identity Center: `jack-admin` selects management
`047260868862`, `jack-prod` production `714000190305`, and `jack-sandbox`
sandbox `070786154596`. Configure profiles with `aws configure sso --profile NAME`
or select an existing per-account configuration through `AWS_CONFIG_FILE`.
Verify STS returns the intended account and an assumed SSO role. `jack-root` is
the retained root profile; use SSO for deployment. Credential outputs are secret:
pipe them into SOPS without plaintext files or terminal output.

## Mail operations

Inbound storage is private. Campaign images have public read access. Bucket names
include the account ID; Lambda logs retain fourteen days. Lists has scoped SES,
queue and object permissions. Auth's SMTP user can send only as
`auth@jackharrhy.dev`, through STARTTLS at
`email-smtp.us-east-1.amazonaws.com:587`.

`receiveEnabled` controls the active inbound receipt rule set and defaults to
false. Auth alone promotes its live SMTP/SOPS/provider configuration and verifies
its verification/recovery mail flow. The AWS owner manages shared resources,
DNS, scoped credentials and Lists configuration.

DNS uses DKIM, MAIL FROM and DMARC for `jackharrhy.dev` and `siliconharbour.dev`.
`jackharrhy.com` uses Zoho; its domain settings supply the DKIM selector.

## Agent skills

`skills-lock.json` pins five official AWS/Pulumi skills by commit, source path
and folder hash. Restore from `aws/` with the skills CLI (verified with 1.7.4):

```sh
DISABLE_TELEMETRY=1 DO_NOT_TRACK=1 npx --yes skills@1.7.4 experimental_install
```

An installed `skills` CLI can run the same command directly. Restored skills and
agent links stay Git-ignored. Review lock changes when updating upstream refs.

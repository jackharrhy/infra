# AWS

Pulumi manages accounts and mail in `us-east-1`:

| Directory     | Project / stack              | Owns                                                                                   |
| ------------- | ---------------------------- | -------------------------------------------------------------------------------------- |
| `foundation/` | `jack-foundation/management` | Protected production/sandbox accounts and Jack's Identity Center access                |
| `mail/`       | `jack-mail/production`       | Production SES, SNS, inbound S3 → Lambda → SQS, campaign media and machine credentials |
| `.`           | `jack-infra/dev`             | Mail resources in management account `047260868862`                                    |

Lists runs on Mug with its SQLite database. Insta-game's Go CLI/CloudFormation
owns game infrastructure separately. Each Pulumi project has its own state in
the local backend. Back up that state and its passphrase together.

## Commands

From `aws/`, install dependencies and load the backend:

```sh
pnpm install --frozen-lockfile
set -a
. /home/jack/infra/aws/.env
set +a
export PULUMI_BACKEND_URL=file:///home/jack/infra/aws
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
`aws:allowedAccountIds` containing only its target account ID:

- Foundation uses `jack-admin`, `managementAccountId`, `ssoInstanceArn`,
  `ownerUserId`, `ownerPermissionSetArn`, and secret `productionEmail` and
  `sandboxEmail` values. Local `Pulumi.management.yaml` is ignored.
- Mail uses `jack-prod`, `accountId`, and `receiveEnabled` (false until inbound
  cutover). Initialize its stack with `pulumi stack init production`.

Verify STS returns the intended account and an assumed SSO role. `jack-root` is
the retained root profile; use SSO for deployment. Credential outputs are secret:
pipe them into SOPS without plaintext files or terminal output.

## Mail operations

Inbound storage is private. Campaign images have public read access. Bucket names
include the account ID; Lambda logs retain fourteen days. Lists has scoped SES,
queue and object permissions. Auth's SMTP user can send only as
`auth@jackharrhy.dev`, through STARTTLS at
`email-smtp.us-east-1.amazonaws.com:587`.

For an account cutover:

1. Back up state, `.env`, a consistent Lists database snapshot, S3 objects with
   metadata, DNS and encrypted runtime configuration. Retain working credentials
   for rollback. Account-bound resources require a separate reviewed preview.
2. Verify both SES domains, DKIM and production access/quota in the target
   account. Preserve MAIL FROM/MX/SPF records until verified. Copy objects under
   their existing keys and compare hashes/metadata; check stored media URLs.
3. Confirm SNS and test simulator delivery/bounce events. Pause Lists, snapshot
   its database and drain the old queue/DLQ. Disable the old receiving rule set
   before enabling the new one to avoid duplicate cross-account receipt.
4. Update Lists' encrypted credentials, region, queues, buckets, configuration
   set and media URL. Auth alone promotes its live SMTP/provider configuration.
   Stage Auth's four encrypted values (`SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`,
   `SMTP_FROM`) in the agreed private `staged/auth-smtp.enc.yaml`, mode 0600,
   using Infra's age recipient explicitly. Use the SES SMTP password output,
   not the AWS secret key. Send Auth the target account/region, staged path,
   verified SES readiness and cutover window before its switch.
5. Verify inbound/DMARC processing, simulator events and media upload/read/delete.
   Auth must accept verification/recovery delivery before credential retirement.
   Retire obsolete resources only after a reviewed destroy preview, preserving
   unrelated resources. Remove unmanaged old Lists keys and orphan Lambda logs.

For rollback, disable new receiving rules, restore old rules and Lists secrets,
then restart Lists. Auth restores its own SMTP configuration. Preserve queues
and new messages for replay. Never test by sending campaigns to subscribers.

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

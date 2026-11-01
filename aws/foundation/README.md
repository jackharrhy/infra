# Accounts and owner access

`jack-foundation/management` owns the production and sandbox member accounts.
It does not own mail or insta-game resources. Account deletion/detachment is
protected; closing accounts is disabled. Recovery emails are secret configuration,
supplied by Jack, with no defaults.

Use the existing local backend, without moving the live mail state:

```sh
export PULUMI_BACKEND_URL=file:///home/jack/infra/aws
set -a
. /home/jack/infra/aws/.env
set +a
cd ~/repos/personal/infra-aws-migration/aws
pnpm install --frozen-lockfile
cd foundation
```

The preparation checkout has not initialized this stack or applied resources.
Once the exact recovery emails are supplied, initialize `management` with the
existing passphrase provider and configure:

| Key                     | Value                                           |
| ----------------------- | ----------------------------------------------- |
| `aws:profile`           | Existing management profile, later `jack-admin` |
| `aws:region`            | `us-east-1`                                     |
| `aws:allowedAccountIds` | Array containing only `047260868862`            |
| `managementAccountId`   | `047260868862`                                  |
| `productionEmail`       | Jack's production recovery address; secret      |
| `sandboxEmail`          | Jack's sandbox recovery address; secret         |

Preview before applying. Initial expected changes are two protected member
accounts and their provider; no existing organization, mail, or fleet replacement.
AWS accounts/Organizations do not themselves add a recurring service charge.

## Non-root owner access

Identity Center is active in `us-east-1`, using instance
`arn:aws:sso:::instance/ssoins-7223972f837dc154` and identity store
`d-906665b671`. The directory user `jack` has ID
`54a87418-5091-7016-8687-976ca035e7cd`. This is not an IAM user.
A portal login alone does not grant account access: it needs a permission set
assigned to that user on an AWS account.

Jack bootstrapped `JackAdministratorAccess` manually: twelve-hour sessions,
AWS-managed `AdministratorAccess`, assigned only to his directory user on
management account `047260868862`. Do not run a competing grant apply.
Verify the permission set, policy attachment and successful management assignment
before configuring all three keys together:

| Key                     | Value                                                                     |
| ----------------------- | ------------------------------------------------------------------------- |
| `ssoInstanceArn`        | Instance ARN above                                                        |
| `ownerUserId`           | Directory user ID above                                                   |
| `ownerPermissionSetArn` | `arn:aws:sso:::permissionSet/ssoins-7223972f837dc154/ps-722356293836bfc8` |

The next preview must import that permission set, policy attachment and management
assignment, not create duplicates. Match the live name and session duration; stop
if the import proposes changes to the bootstrap. Production and sandbox assignments
are new resources, planned alongside the two protected member accounts. Omitting
all three SSO keys previews accounts only; partial configuration fails closed.
Jack confirmed both recovery addresses, including the corrected sandbox address.
Store those exact values as secret configuration; do not use placeholders.
The import preserves the existing name and twelve-hour session duration.

Jack must first run `aws configure sso --profile jack-admin` and complete SSO
login. Profile configuration is operator-owned; do not work around a denied write
to `~/.aws/config`. Verify `aws sts get-caller-identity --profile jack-admin`
returns account `047260868862` with an assumed SSO role, not root, before running
the foundation preview. No member accounts or member profiles exist yet.

After account creation, create CLI profiles `jack-prod` and `jack-sandbox`, selecting the
corresponding account and permission set. Verify each with `aws sts
get-caller-identity` and test actual CLI access. Existing root keys stay in place
until working non-root access and recovery have been confirmed.

The existing `jack` profile authenticates as root. Use the named non-root
profiles for ongoing cross-account deployment; do not pretend a profile is ready
until its STS check succeeds.

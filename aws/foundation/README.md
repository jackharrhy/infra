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

| Key | Value |
| --- | --- |
| `aws:profile` | Existing management profile, later `jack-admin` |
| `aws:region` | `us-east-1` |
| `aws:allowedAccountIds` | Array containing only `047260868862` |
| `managementAccountId` | `047260868862` |
| `productionEmail` | Jack's production recovery address; secret |
| `sandboxEmail` | Jack's sandbox recovery address; secret |

Preview before applying. Initial expected changes are two protected member
accounts and their provider; no existing organization, mail, or fleet replacement.
AWS accounts/Organizations do not themselves add a recurring service charge.

## Non-root owner access

No organization Identity Center instance was found in the 17 enabled regions.
The public CreateInstance API cannot create one in the management account:
https://docs.aws.amazon.com/singlesignon/latest/APIReference/API_CreateInstance.html

Enable an organization instance in `us-east-1` through the console. Choose
single-region and the default AWS-managed encryption key; multi-region/customer
managed KMS options can add charges. Use Identity Center's built-in directory.
Create Jack's owner user and complete its password/MFA enrollment. Do not replace
this step with new permanent root or broadly privileged IAM access keys.

After discovering the instance ARN and owner user ID, set `ssoInstanceArn` and
`ownerUserId` together and review another preview. This adds a four-hour
`JackAdministrator` permission set and owner assignments to all three accounts.
These are human owner permissions, not permissions for Lists or game workloads.

Create CLI profiles `jack-admin`, `jack-prod`, and `jack-sandbox`, selecting the
corresponding account and permission set. Verify each with `aws sts
get-caller-identity` and test actual CLI access. Existing root keys stay in place
until working non-root access and recovery have been confirmed.

The existing `jack` profile authenticates as root and cannot be used as a normal
cross-account AssumeRole source. Do not pretend an assumed-role profile is ready
until its STS check succeeds.

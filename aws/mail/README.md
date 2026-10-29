# Production mail

`jack-mail/production` owns SES, SNS, inbound S3/Lambda/SQS, public campaign
media, the Lists machine user, and Jack Auth's sender-scoped SMTP user in the
new production member account. Lists stays on Mug with its SQLite database.
Insta-game resources remain owned by its Go CLI/CloudFormation in sandbox.

The root `jack-infra/dev` project remains live during preparation. This new
project creates replacements in another account; changing state names or aliases
cannot move the existing AWS objects between accounts. Do not apply the new
project against the management account; its account guard rejects that target.

Use the same local backend/passphrase setup as `../foundation`. No S3 state
backend, Pulumi Cloud subscription, Control Tower, customer-managed KMS key, or
other paid administration service is needed for this phase.

## Configuration

After production account creation and a successful `jack-prod` STS check,
initialize the `production` stack and set:

| Key | Value |
| --- | --- |
| `aws:profile` | `jack-prod` |
| `aws:region` | `us-east-1` |
| `aws:allowedAccountIds` | Array containing only the new production ID |
| `accountId` | Same production ID |
| `receiveEnabled` | `false` until the coordinated inbound cutover |

Install once from the parent AWS workspace with `pnpm install --frozen-lockfile`;
run `pnpm run check` in this project, then review
`pnpm run pulumi:preview`. Expected replacements are account-bound resources
created in this new state. The preview must not touch the old state/resources.

Bucket names include the new account ID. Both use standard storage; inbound is
private and only campaign images have public read access. New mail resources
have the same service footprint as the old pipeline. SES/messages, S3 storage
and requests, SNS, SQS and Lambda remain usage-billed; an overlap period can
briefly duplicate small existing charges. Current copied data is under 1 MiB,
excluding the application's SQLite snapshot. Lambda logs are explicitly owned with 14-day retention, so retirement does not
leave an unmanaged log group. No paid networking or servers are
introduced. Review actual account/configuration changes before applying.

Access-key/SMTP outputs are secrets. Write them directly into staged SOPS files
or a private process; never print decrypted outputs or put keys on command lines.
Do not merge staged deployment-secret changes before their cutover is ready.

## Cutover owners

The AWS migration owner manages target resources, scoped IAM/SMTP credentials,
SES verification, shared DNS, and Lists deployment configuration. Auth alone
promotes live Jack Auth SOPS/runtime/provider configuration and accepts its
verification/recovery mail flow. Never edit that live configuration concurrently.

Agree a separate encrypted staging path and key schema with Auth first. The
proposed path is the private migration artifact directory's
`staged/auth-smtp.enc.yaml`, outside live SOPS paths. Before the live switch,
send Auth the target account/region, staged encrypted path, verified sender/SES
readiness and a proposed window. Share paths and readiness, never secret values.
Tea consumer cutover is independent.

## Cutover

1. Verify recoverable encrypted backups of local state plus `.env`, the Lists
   SQLite database, S3 contents and metadata, and deployment/DNS configuration.
   Preserve the last working secrets for rollback.
2. Apply the reviewed new-account preview. Leave incoming receipt rules inactive.
3. Add the new account's DKIM/verification DNS alongside the old records. Keep
   existing MAIL FROM, MX and SPF settings until their replacement is verified.
   Verify both sender domains and request SES production access if required.
   A new account's SES sandbox status/quota does not inherit the old account's.
4. Copy inbound objects and media under their existing keys, preserving content
   type/cache metadata. Compare object counts and SHA-256 hashes. Keep the old
   media bucket until existing URLs in live data have been assessed. The first
   snapshot found no old media-bucket references in stored text fields.
5. Confirm the new SNS subscription and test delivery/bounce events with the
   SES mailbox simulator. Do not send campaigns or test blasts to subscribers.
6. In a brief maintenance window, pause only Lists' container, take a fresh
   consistent SQLite snapshot, and confirm the old queue/DLQ have drained.
   Disable the old receipt rule set before activating the new one: SES processes
   matching receipt rules in multiple accounts simultaneously.
7. Stage only the agreed encrypted Auth credentials. Auth's owner alone
   promotes its SOPS/SMTP/provider configuration and switches ZITADEL.
   Preserve sender `auth@jackharrhy.dev`, `ses:SendRawEmail`-only permission,
   the SES configuration set and STARTTLS on port 587. The AWS migration owner
   updates Lists' credentials, region, buckets, queue URL, configuration set and
   media base URL. Each owner restarts only their affected services.
8. Test Lists health, one controlled simulator send/event, inbound processing,
   DMARC ingestion, and media upload/read/delete. Have Auth's owner verify its
   login/verification SMTP path. Check durable attempts/events and object keys,
   not just HTTP health. Auth must explicitly accept its new provider and
   verification/recovery flow before old SMTP credentials or sender resources
   are retired. Resume normal operation only after these pass.
9. Retire old owned mail resources deliberately from `jack-infra/dev`, after a
   reviewed destroy preview and data/queue verification. Back up its final state
   and remove only obsolete DNS/credentials. Inventory and remove the old Lists
   user's unmanaged access keys only after its replacement works; otherwise IAM
   user deletion will fail. Verify/delete the old function's implicitly created
   CloudWatch log group after preserving useful evidence. Keep unrelated management/fleet
   infrastructure. Remove the root project's source only once its state is empty.

For rollback, the AWS migration owner restores Lists' old encrypted runtime
secrets, disables the new receipt set, re-enables the old one, and restarts Lists.
Auth's owner alone restores its old SMTP/provider configuration. Preserve new-account messages for replay; never discard a queue as
part of rollback. Existing source resources/keys remain until end-to-end proof
and the explicit retirement step, not as permanent duplicate deployments.

## Current evidence

The private migration artifact directory on Terrabud records live inventory,
state exports, encrypted backups, integrity checks, and offhost checksums. At
preparation, live Lists had 2 users, 14 subscribers, 2 campaigns and 12 messages;
there were 37 inbound S3 objects, 1 media object, and empty queue/DLQ counts.
Take a fresh snapshot before cutover; these are not claims about future state.

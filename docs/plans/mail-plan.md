# SES Inbound Email Pipeline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Receive inbound email at `reply.jackharrhy.dev`, store raw `.eml` in S3, queue metadata via SQS, and consume it with a Go service on the mug VPS for listmonk reply tracking.

**Architecture:** SES inbound stores `.eml` in S3 and invokes a Lambda that pushes metadata to SQS. A Go service (`mail-ingest`) on the mug VPS long-polls SQS and stores metadata in SQLite, serving a password-protected web UI at `replies.jackharrhy.dev`.

**Tech Stack:** Pulumi (TypeScript), AWS SES/S3/Lambda/SQS/IAM, octodns (DNS), Go + SQLite (consumer service), Docker Compose + Traefik (mug deployment)

**Design doc:** `docs/plans/2026-03-09-ses-inbound-design.md`

**Related plans:**
- Go service (part 1): `docs/plans/2026-03-09-mail-ingest-plan.md`
- Go service (part 2, threaded replies): `docs/plans/2026-03-09-mail-ingest-replies-plan.md`

---

### Task 1: Add DNS record for SES inbound

**Files:**
- Modify: `dns/zones/jackharrhy.dev.yaml`

**Step 1: Add `reply` MX record**

Add the `reply` subdomain entry to `dns/zones/jackharrhy.dev.yaml`:

```yaml
reply:
  type: MX
  value:
    exchange: inbound-smtp.us-east-1.amazonaws.com.
    preference: 10
```

**Step 2: Dry-run octodns to verify**

Run: `uv run cli.py dns --dry-run`
Expected: Shows the new MX record as an addition, no unexpected changes.

**Step 3: Commit**

```bash
git add dns/zones/jackharrhy.dev.yaml
git commit -m "feat: add reply.jackharrhy.dev MX record for SES inbound"
```

---

### Task 2: Create S3 bucket for inbound email

**Files:**
- Modify: `aws/index.ts`

**Step 1: Add pulumi import and S3 bucket**

Add `import * as pulumi from "@pulumi/pulumi";` to the top of `aws/index.ts` (alongside the existing `aws` import), then append:

```typescript
const inboundEmailBucket = new aws.s3.BucketV2("ses-inbound-email", {
  bucket: "ses-inbound-email",
  forceDestroy: false,
});

new aws.s3.BucketPublicAccessBlock("ses-inbound-email-public-access-block", {
  bucket: inboundEmailBucket.id,
  blockPublicAcls: true,
  blockPublicPolicy: true,
  ignorePublicAcls: true,
  restrictPublicBuckets: true,
});
```

**Step 2: Add bucket policy allowing SES to write**

```typescript
new aws.s3.BucketPolicy("ses-inbound-email-policy", {
  bucket: inboundEmailBucket.id,
  policy: pulumi.all([inboundEmailBucket.arn, accountId]).apply(([bucketArn, id]) =>
    JSON.stringify({
      Version: "2012-10-17",
      Statement: [
        {
          Sid: "AllowSESPut",
          Effect: "Allow",
          Principal: { Service: "ses.amazonaws.com" },
          Action: "s3:PutObject",
          Resource: `${bucketArn}/*`,
          Condition: {
            StringEquals: { "AWS:SourceAccount": id },
          },
        },
      ],
    }),
  ),
});
```

**Step 3: Verify with Pulumi preview**

Run: `pulumi preview` (from `aws/` directory)
Expected: 3 resources to create (BucketV2, BucketPublicAccessBlock, BucketPolicy). No changes to existing resources.

**Step 4: Deploy**

Run: `pulumi up --yes` (from `aws/` directory)
Expected: 3 resources created.

**Step 5: Commit**

```bash
git add aws/index.ts
git commit -m "feat: add S3 bucket for SES inbound email storage"
```

---

### Task 3: Create SQS queues

**Files:**
- Modify: `aws/index.ts`

**Step 1: Add dead-letter queue**

```typescript
const inboundEmailDLQ = new aws.sqs.Queue("ses-inbound-email-dlq", {
  name: "ses-inbound-email-dlq",
  messageRetentionSeconds: 1209600, // 14 days
});
```

**Step 2: Add main queue with DLQ redrive policy**

```typescript
const inboundEmailQueue = new aws.sqs.Queue("ses-inbound-email-queue", {
  name: "ses-inbound-email-queue",
  visibilityTimeoutSeconds: 60,
  messageRetentionSeconds: 345600, // 4 days
  redrivePolicy: inboundEmailDLQ.arn.apply((dlqArn) =>
    JSON.stringify({
      deadLetterTargetArn: dlqArn,
      maxReceiveCount: 3,
    }),
  ),
});
```

**Step 3: Verify with Pulumi preview**

Run: `pulumi preview` (from `aws/` directory)
Expected: 2 new resources (Queue, Queue). No changes to existing resources.

**Step 4: Deploy**

Run: `pulumi up --yes` (from `aws/` directory)
Expected: 2 resources created.

**Step 5: Commit**

```bash
git add aws/index.ts
git commit -m "feat: add SQS queues for inbound email processing"
```

---

### Task 4: Create Lambda bridge (SES -> SQS)

**Files:**
- Modify: `aws/index.ts`

**Step 1: Add Lambda IAM role with SQS write permission**

```typescript
const inboundEmailLambdaRole = new aws.iam.Role("ses-inbound-email-lambda-role", {
  assumeRolePolicy: aws.iam.assumeRolePolicyForPrincipal({
    Service: "lambda.amazonaws.com",
  }),
});

new aws.iam.RolePolicyAttachment("ses-inbound-email-lambda-basic-execution", {
  role: inboundEmailLambdaRole.name,
  policyArn: aws.iam.ManagedPolicy.AWSLambdaBasicExecutionRole,
});

new aws.iam.RolePolicy("ses-inbound-email-lambda-sqs-write", {
  role: inboundEmailLambdaRole.name,
  policy: inboundEmailQueue.arn.apply((queueArn) =>
    JSON.stringify({
      Version: "2012-10-17",
      Statement: [
        {
          Effect: "Allow",
          Action: "sqs:SendMessage",
          Resource: queueArn,
        },
      ],
    }),
  ),
});
```

**Step 2: Add the Lambda function**

The Lambda receives an SES event, extracts metadata, and pushes it to SQS. It does NOT parse MIME.

```typescript
const inboundEmailLambda = new aws.lambda.CallbackFunction("ses-inbound-email-lambda", {
  role: inboundEmailLambdaRole,
  timeout: 30,
  memorySize: 128,
  environment: {
    variables: {
      SQS_QUEUE_URL: inboundEmailQueue.url,
    },
  },
  callback: async (event: any) => {
    const record = event.Records?.[0];
    if (!record?.ses) {
      console.error("No SES record found");
      return { disposition: "STOP_RULE" };
    }

    const mail = record.ses.mail;
    const receipt = record.ses.receipt;

    const payload = {
      messageId: mail.messageId,
      timestamp: mail.timestamp,
      source: mail.source,
      from: mail.commonHeaders?.from,
      to: mail.commonHeaders?.to,
      subject: mail.commonHeaders?.subject,
      spamVerdict: receipt.spamVerdict?.status,
      virusVerdict: receipt.virusVerdict?.status,
      spfVerdict: receipt.spfVerdict?.status,
      dkimVerdict: receipt.dkimVerdict?.status,
      dmarcVerdict: receipt.dmarcVerdict?.status,
      action: receipt.action,
    };

    const { SQSClient, SendMessageCommand } = require("@aws-sdk/client-sqs");
    const sqs = new SQSClient({});

    await sqs.send(
      new SendMessageCommand({
        QueueUrl: process.env.SQS_QUEUE_URL,
        MessageBody: JSON.stringify(payload),
        MessageAttributes: {
          messageId: {
            DataType: "String",
            StringValue: mail.messageId,
          },
        },
      }),
    );

    console.log(`Queued message ${mail.messageId}`);
    return { disposition: "CONTINUE" };
  },
});
```

**Step 3: Add SES permission to invoke the Lambda**

```typescript
new aws.lambda.Permission("ses-invoke-inbound-email-lambda", {
  action: "lambda:InvokeFunction",
  function: inboundEmailLambda.name,
  principal: "ses.amazonaws.com",
  sourceAccount: accountId,
});
```

**Step 4: Verify with Pulumi preview**

Run: `pulumi preview` (from `aws/` directory)
Expected: New resources for IAM role, policy attachment, inline policy, Lambda function, and Lambda permission. No changes to existing resources.

**Step 5: Deploy**

Run: `pulumi up --yes` (from `aws/` directory)
Expected: Resources created.

**Step 6: Commit**

```bash
git add aws/index.ts
git commit -m "feat: add Lambda bridge from SES inbound to SQS"
```

---

### Task 5: Create SES receipt rule set and rule

**Files:**
- Modify: `aws/index.ts`

**Step 1: Add the receipt rule set and activate it**

```typescript
const inboundRuleSet = new aws.ses.ReceiptRuleSet("ses-inbound-rule-set", {
  ruleSetName: "ses-inbound-rules",
});

new aws.ses.ActiveReceiptRuleSet("ses-inbound-active-rule-set", {
  ruleSetName: inboundRuleSet.ruleSetName,
});
```

**Step 2: Add the receipt rule**

```typescript
new aws.ses.ReceiptRule("ses-inbound-receipt-rule", {
  name: "store-and-forward",
  ruleSetName: inboundRuleSet.ruleSetName,
  recipients: ["reply.jackharrhy.dev"],
  enabled: true,
  scanEnabled: true,
  s3Actions: [
    {
      bucketName: inboundEmailBucket.bucket,
      objectKeyPrefix: "inbound/",
      position: 1,
    },
  ],
  lambdaActions: [
    {
      functionArn: inboundEmailLambda.arn,
      invocationType: "Event",
      position: 2,
    },
  ],
});
```

**Step 3: Verify with Pulumi preview**

Run: `pulumi preview` (from `aws/` directory)
Expected: 3 new resources (ReceiptRuleSet, ActiveReceiptRuleSet, ReceiptRule). No changes to existing resources.

**Step 4: Deploy**

Run: `pulumi up --yes` (from `aws/` directory)
Expected: Resources created.

**Step 5: Commit**

```bash
git add aws/index.ts
git commit -m "feat: add SES receipt rule for inbound email on reply.jackharrhy.dev"
```

---

### Task 6: Create IAM user for the mug Go service

**Files:**
- Modify: `aws/index.ts`

**Step 1: Add IAM user with SQS read and S3 read permissions**

```typescript
const mailIngestUser = new aws.iam.User("mail-ingest", {
  name: "mail-ingest",
});

new aws.iam.UserPolicy("mail-ingest-policy", {
  user: mailIngestUser.name,
  policy: pulumi
    .all([inboundEmailQueue.arn, inboundEmailDLQ.arn, inboundEmailBucket.arn])
    .apply(([queueArn, dlqArn, bucketArn]) =>
      JSON.stringify({
        Version: "2012-10-17",
        Statement: [
          {
            Sid: "SQSRead",
            Effect: "Allow",
            Action: [
              "sqs:ReceiveMessage",
              "sqs:DeleteMessage",
              "sqs:GetQueueAttributes",
              "sqs:ChangeMessageVisibility",
            ],
            Resource: [queueArn, dlqArn],
          },
          {
            Sid: "S3Read",
            Effect: "Allow",
            Action: ["s3:GetObject"],
            Resource: `${bucketArn}/*`,
          },
        ],
      }),
    ),
});
```

**Step 2: Create access key**

Note: Pulumi can create the access key, but the secret is only available at creation time. Create it manually after deploy:

Run: `aws iam create-access-key --user-name mail-ingest --profile jack`

Store the output `AccessKeyId` and `SecretAccessKey` for the next task.

**Step 3: Verify with Pulumi preview**

Run: `pulumi preview` (from `aws/` directory)
Expected: 2 new resources (User, UserPolicy). No changes to existing resources.

**Step 4: Deploy**

Run: `pulumi up --yes` (from `aws/` directory)
Expected: 2 resources created.

**Step 5: Commit**

```bash
git add aws/index.ts
git commit -m "feat: add IAM user for mail-ingest service"
```

---

### Task 7: Add mail-ingest service to mug compose

**Files:**
- Modify: `hosts/mug/compose.yml`
- Create: `hosts/mug/secrets/mail-ingest.env` (SOPS-encrypted)

**Step 1: Add service to compose.yml**

Add before the `networks:` block in `hosts/mug/compose.yml`:

```yaml
  mail-ingest:
    image: ghcr.io/jackharrhy/mail-ingest:main
    restart: always
    networks: [web]
    env_file:
      - ./.runtime-secrets/mail-ingest.env
    volumes:
      - ./volumes/mail_ingest_data:/data
    labels:
      - "traefik.docker.network=mug_web"
      - "traefik.enable=true"
      - "traefik.http.services.mail-ingest.loadbalancer.server.port=8080"
      - "traefik.http.routers.mail-ingest.rule=Host(`replies.jackharrhy.dev`)"
      - "traefik.http.routers.mail-ingest.entrypoints=websecure"
      - "traefik.http.routers.mail-ingest.tls.certresolver=mugresolver"
```

**Step 2: Create SOPS-encrypted secrets file**

Create `hosts/mug/secrets/mail-ingest.env` with:

```
AWS_ACCESS_KEY_ID=<from task 6 step 2>
AWS_SECRET_ACCESS_KEY=<from task 6 step 2>
AWS_REGION=us-east-1
SQS_QUEUE_URL=<from pulumi stack output>
S3_BUCKET=ses-inbound-email
AUTH_PASSWORD=<generate a strong password>
DB_PATH=/data/mail-ingest.db
```

Encrypt: `sops --encrypt --in-place hosts/mug/secrets/mail-ingest.env`

**Step 3: Add volume directory to ensure-volumes.sh**

Add `mail_ingest_data` to `scripts/ensure-volumes.sh` if it manages volume directories.

**Step 4: Commit**

```bash
git add hosts/mug/compose.yml hosts/mug/secrets/mail-ingest.env
git commit -m "feat: add mail-ingest service to mug compose"
```

---

### Task 8: Apply DNS and end-to-end test

**Step 1: Apply the DNS changes**

Run: `uv run cli.py dns`
Expected: MX record for `reply.jackharrhy.dev` created.

**Step 2: Verify DNS propagation**

Run: `dig MX reply.jackharrhy.dev`
Expected: `10 inbound-smtp.us-east-1.amazonaws.com.`

**Step 3: Send a test email**

Send an email to `test@reply.jackharrhy.dev` from an external account.

**Step 4: Verify S3 storage**

Run: `aws s3 ls s3://ses-inbound-email/inbound/ --profile jack`
Expected: A new `.eml` object appears.

**Step 5: Verify Lambda -> SQS**

Run: `aws logs tail /aws/lambda/ses-inbound-email-lambda --profile jack --since 5m`
Expected: Log entry showing `Queued message <id>`.

Run: `aws sqs get-queue-attributes --queue-url <queue-url> --attribute-names ApproximateNumberOfMessages --profile jack`
Expected: Message count > 0 (or 0 if mail-ingest already consumed it).

**Step 6: Commit (if any adjustments were made)**

```bash
git add -A
git commit -m "chore: adjustments from end-to-end testing"
```

---

### Task 9: DMARC hardening

**Files:**
- Modify: `dns/zones/jackharrhy.dev.yaml`

This task should be done AFTER the full pipeline has been validated and running for a monitoring period.

**Step 1: Tighten DMARC to quarantine**

Change the `_dmarc` TXT record in `dns/zones/jackharrhy.dev.yaml`:

```yaml
_dmarc:
  type: TXT
  value: v=DMARC1\; p=quarantine\;
```

**Step 2: Apply DNS**

Run: `uv run cli.py dns`

**Step 3: Monitor**

Watch for any legitimate email delivery issues over 1-2 weeks.

**Step 4: Tighten DMARC to reject**

```yaml
_dmarc:
  type: TXT
  value: v=DMARC1\; p=reject\;
```

**Step 5: Apply and commit**

```bash
uv run cli.py dns
git add dns/zones/jackharrhy.dev.yaml
git commit -m "feat: harden DMARC policy to reject for jackharrhy.dev"
```

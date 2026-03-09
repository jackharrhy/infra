# SES Inbound Email Pipeline + Reply Tracker Design

## Goal

Receive inbound email at `reply.jackharrhy.dev` via AWS SES, store raw messages in S3, queue metadata via SQS, and consume it with a Go service on the mug VPS that provides a password-protected web UI for browsing listmonk reply tracking.

## Architecture

```
Internet -> MX reply.jackharrhy.dev -> SES inbound
  -> Receipt Rule:
      1. Store .eml in S3 (ses-inbound-email/inbound/)
      2. Invoke Lambda
  -> Lambda extracts metadata, pushes to SQS
  -> SQS queue (ses-inbound-email-queue)
  -> Go service on mug (long-polls SQS)
      -> stores metadata in SQLite
      -> serves password-protected web UI
      -> links to S3 for raw .eml via presigned URLs
```

## AWS Resources (Pulumi)

All defined in `aws/index.ts`:

| Resource | Purpose |
|----------|---------|
| `aws.s3.BucketV2` | Store raw .eml files |
| `aws.s3.BucketPublicAccessBlock` | Lock bucket down |
| `aws.s3.BucketPolicy` | Allow SES to write |
| `aws.ses.ReceiptRuleSet` | Rule set container |
| `aws.ses.ActiveReceiptRuleSet` | Activate it |
| `aws.ses.ReceiptRule` | Match `reply.jackharrhy.dev`, S3 + Lambda actions |
| `aws.lambda.CallbackFunction` | Extract SES event metadata, push to SQS |
| `aws.iam.Role` + policy | Lambda execution (SQS write + CloudWatch logs) |
| `aws.sqs.Queue` | Durable message queue |
| `aws.sqs.Queue` (DLQ) | Dead-letter queue for failed messages |
| `aws.iam.User` + policy | Credentials for Go service (SQS read + S3 read) |

## DNS

Add to `dns/zones/jackharrhy.dev.yaml`:

- `reply` MX record -> `inbound-smtp.us-east-1.amazonaws.com`
- `replies` will be handled by existing wildcard A/AAAA records pointing to mug

## Go Service (mail-ingest)

- **Repo:** `jackharrhy/mail-ingest` (new, separate repo)
- **Image:** `ghcr.io/jackharrhy/mail-ingest:main`
- **Host:** `replies.jackharrhy.dev` on mug via Traefik
- **Storage:** SQLite at `/data/mail-ingest.db`
- **Deployment:** Watchtower auto-updates from GHCR

Functionality:
- Long-polls SQS for new message metadata
- Stores sender, subject, date, spam/DKIM/SPF/DMARC verdicts, S3 key in SQLite
- Serves HTML UI (server-rendered templates, no JS framework) behind a password
- List view of replies with metadata columns
- Click-through to raw .eml via S3 presigned URL

### Compose Definition (`hosts/mug/compose.yml`)

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

### Environment Variables (`.runtime-secrets/mail-ingest.env`)

- `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` -- IAM user credentials
- `AWS_REGION=us-east-1`
- `SQS_QUEUE_URL` -- queue URL from Pulumi output
- `S3_BUCKET=ses-inbound-email`
- `AUTH_PASSWORD` -- password for web UI access
- `DB_PATH=/data/mail-ingest.db`

## DMARC Hardening (follow-up)

After validating inbound+outbound flows:
1. Move `p=none` to `p=quarantine` in `dns/zones/jackharrhy.dev.yaml`
2. Monitor for a period
3. Move to `p=reject`

## Out of Scope

- MIME parsing / attachment extraction
- Reply-to-listmonk integration (linking replies to campaigns)
- The Go service implementation itself (separate repo, separate plan)

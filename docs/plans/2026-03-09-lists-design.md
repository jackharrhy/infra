# `lists` -- Personal Newsletter Service Design

## Goal

A personal newsletter service that replaces listmonk. Handles subscriber management (with independent topic lists), campaign sending via SES API (no SMTP), inbound reply tracking via SQS, and email compliance. Built with TypeScript, react-email templates, and SQLite.

## What it replaces

- **listmonk** -- full replacement (subscribers, campaigns, sending, compliance)
- **mail-ingest** -- absorbed (inbound email tracking + reply capability)

## Tech Stack

| Layer | Choice |
|-------|--------|
| Runtime | Bun |
| HTTP | Hono |
| Database | bun:sqlite + Drizzle ORM |
| Email templates | react-email (native import) |
| Email rendering | markdown -> HTML -> react-email `render()` |
| Email sending | AWS SDK v3 SESv2 `SendEmail` (raw message, no SMTP) |
| Inbound | AWS SDK v3 SQS long-poll + S3 presigned URLs |
| Admin UI | Hono JSX (server-rendered, no client-side framework) |
| Public pages | Hono JSX (server-rendered) |

## Data Model (Drizzle schema)

### subscribers

| Column | Type | Notes |
|--------|------|-------|
| id | integer PK | autoincrement |
| email | text | unique, lowercase |
| name | text | optional |
| status | text | `active` / `unsubscribed` / `blocklisted` |
| unsubscribe_token | text | unique, for preference/unsubscribe URLs |
| created_at | text | datetime |
| confirmed_at | text | nullable, set on double opt-in confirm |

### lists

| Column | Type | Notes |
|--------|------|-------|
| id | integer PK | autoincrement |
| slug | text | unique, e.g. `plow`, `projects`, `siliconharbour` |
| name | text | display name |
| description | text | shown on subscribe page |

### subscriber_lists

| Column | Type | Notes |
|--------|------|-------|
| subscriber_id | integer FK | |
| list_id | integer FK | |
| status | text | `unconfirmed` / `confirmed` / `unsubscribed` |
| subscribed_at | text | datetime |

Composite PK on (subscriber_id, list_id).

### campaigns

| Column | Type | Notes |
|--------|------|-------|
| id | integer PK | autoincrement |
| list_id | integer FK | which list this targets |
| subject | text | email subject line |
| body_markdown | text | campaign content as markdown |
| template_slug | text | which react-email template to use (default: `newsletter`) |
| from_address | text | e.g. `plow@jackharrhy.dev` |
| status | text | `draft` / `sending` / `sent` |
| sent_at | text | nullable |
| created_at | text | datetime |

### campaign_sends

| Column | Type | Notes |
|--------|------|-------|
| id | integer PK | autoincrement |
| campaign_id | integer FK | |
| subscriber_id | integer FK | |
| ses_message_id | text | SES response message ID |
| status | text | `pending` / `sent` / `bounced` |
| sent_at | text | nullable |

### inbound_messages

| Column | Type | Notes |
|--------|------|-------|
| id | integer PK | autoincrement |
| message_id | text | unique, SES message ID |
| timestamp | text | |
| source | text | sender email |
| from_addrs | text | JSON array |
| to_addrs | text | JSON array |
| subject | text | |
| spam_verdict | text | nullable |
| virus_verdict | text | nullable |
| spf_verdict | text | nullable |
| dkim_verdict | text | nullable |
| dmarc_verdict | text | nullable |
| s3_key | text | nullable |
| campaign_id | integer FK | nullable, links reply to originating campaign |
| created_at | text | datetime |

### replies

| Column | Type | Notes |
|--------|------|-------|
| id | integer PK | autoincrement |
| inbound_message_id | integer FK | |
| from_addr | text | |
| to_addr | text | |
| subject | text | |
| body | text | |
| ses_message_id | text | nullable |
| in_reply_to | text | nullable, Message-ID header |
| sent_at | text | datetime |

## Project Structure

```
lists/
├── src/
│   ├── index.ts              # entry point: start server + SQS poller
│   ├── config.ts             # env var loading + validation
│   ├── db/
│   │   ├── schema.ts         # Drizzle schema (all tables)
│   │   ├── index.ts          # DB connection
│   │   └── migrate.ts        # migration runner
│   ├── routes/
│   │   ├── admin.tsx         # admin UI (Hono JSX)
│   │   ├── public.tsx        # subscribe/confirm/unsubscribe
│   │   └── api.ts            # JSON API for external projects
│   ├── services/
│   │   ├── sender.ts         # campaign sending (iterate subscribers, render, SES)
│   │   ├── poller.ts         # SQS long-poll loop for inbound
│   │   ├── subscriber.ts     # subscribe, confirm, unsubscribe logic
│   │   └── bounce.ts         # bounce/complaint processing
│   ├── auth.ts               # session cookie middleware (admin)
│   └── compliance.ts         # token generation, List-Unsubscribe headers
├── emails/
│   ├── templates/
│   │   ├── newsletter.tsx    # campaign wrapper (header, content slot, footer, unsub)
│   │   ├── confirm.tsx       # double opt-in confirmation
│   │   └── welcome.tsx       # post-confirmation welcome
│   └── components/           # shared react-email components
├── drizzle/                  # generated migrations
├── drizzle.config.ts
├── package.json
├── tsconfig.json
├── Dockerfile
└── .github/workflows/build.yml
```

## HTTP Routes

### Public (no auth)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/subscribe` | Subscription form (pick lists) |
| POST | `/subscribe` | Submit subscription (triggers confirm email) |
| GET | `/confirm/:token` | Double opt-in confirmation link |
| GET | `/preferences/:token` | Manage list subscriptions |
| POST | `/preferences/:token` | Update list preferences |
| GET | `/unsubscribe/:token` | One-click unsubscribe (also handles RFC 8058 POST) |
| POST | `/unsubscribe/:token` | RFC 8058 one-click unsubscribe via POST |

### API (bearer token via `API_TOKEN` env var)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/subscribers` | Add subscriber + subscribe to lists |
| GET | `/api/subscribers` | List subscribers |
| DELETE | `/api/subscribers/:id` | Remove subscriber |
| POST | `/api/campaigns/:id/send` | Trigger campaign send |

### Admin UI (password session auth)

| Method | Path | Description |
|--------|------|-------------|
| GET/POST | `/admin/login` | Login |
| GET | `/admin/` | Dashboard |
| GET | `/admin/subscribers` | Subscriber list |
| GET | `/admin/lists` | List management |
| GET/POST | `/admin/lists/new` | Create list |
| GET | `/admin/campaigns` | Campaign list |
| GET/POST | `/admin/campaigns/new` | New campaign (markdown editor) |
| GET | `/admin/campaigns/:id` | Campaign detail |
| POST | `/admin/campaigns/:id/preview` | Preview rendered email |
| POST | `/admin/campaigns/:id/send` | Send campaign |
| GET | `/admin/inbound` | Inbound message list |
| GET | `/admin/inbound/:id` | Message detail + reply form |
| POST | `/admin/inbound/:id/reply` | Send threaded reply |

## Campaign Sending Flow

```typescript
const campaign = await db.query.campaigns.findFirst({ where: eq(campaigns.id, id) });
const subscribers = await getConfirmedSubscribers(db, campaign.listId);

const bodyHtml = marked(campaign.bodyMarkdown);

for (const subscriber of subscribers) {
  const unsubUrl = `${BASE_URL}/unsubscribe/${subscriber.unsubscribeToken}`;

  const html = await render(NewsletterTemplate({
    content: bodyHtml,
    subject: campaign.subject,
    unsubscribeUrl: unsubUrl,
    preferencesUrl: `${BASE_URL}/preferences/${subscriber.unsubscribeToken}`,
  }));

  const text = toPlainText(html);

  await ses.send(new SendEmailCommand({
    Content: {
      Raw: { Data: buildRawEmail({
        from: campaign.fromAddress,
        to: subscriber.email,
        subject: campaign.subject,
        html, text,
        listUnsubscribe: unsubUrl,
      }) },
    },
  }));
}
```

No SMTP. Direct SES API calls via AWS SDK v3.

## Compliance (non-negotiable)

- **`List-Unsubscribe` header** with HTTPS URL on every campaign email
- **`List-Unsubscribe-Post: List-Unsubscribe=One-Click`** header (RFC 8058)
- **Visible unsubscribe link** in email footer
- **Double opt-in** -- confirmation email on subscribe, `unconfirmed` until clicked
- **Bounce handling** -- existing SNS topic for SES bounce/complaint events; route to the service to auto-blocklist hard bounces and complaints
- **Physical address** in email footer (CAN-SPAM)

## Environment Variables

| Var | Purpose |
|-----|---------|
| `AWS_ACCESS_KEY_ID` | IAM credentials (SES send + SQS read + S3 read) |
| `AWS_SECRET_ACCESS_KEY` | IAM credentials |
| `AWS_REGION` | `us-east-1` |
| `SQS_QUEUE_URL` | Inbound email queue |
| `S3_BUCKET` | Raw .eml storage |
| `AUTH_PASSWORD` | Admin UI password |
| `API_TOKEN` | Bearer token for external API |
| `DB_PATH` | SQLite database path |
| `FROM_DOMAIN` | `jackharrhy.dev` |
| `BASE_URL` | `https://lists.jackharrhy.dev` |

## Infra Changes (in the infra repo)

- Update `hosts/mug/compose.yml`: replace `listmonk` + `listmonk_db` services with single `lists` service (image: `ghcr.io/jackharrhy/lists:main`)
- Update `mail-plan.md` references: image name changes from `mail-ingest` to `lists`
- The `listmonk` Postgres database can be decommed
- The `listmonk-ses-smtp` IAM user + `AWSSESSendingGroupDoNotRename` group can be decommed after migration
- The `mail-ingest` IAM user gets renamed/repurposed as the `lists` IAM user
- Route SES bounce/complaint SNS subscription to the new service instead of listmonk's webhook

## Migration from listmonk

One-time steps:
1. Export subscribers from listmonk (API or direct DB query)
2. Import into `lists` SQLite via a migration script
3. Verify subscriber counts match
4. Switch DNS / Traefik routing from listmonk to lists
5. Decom listmonk + Postgres containers
6. Clean up SMTP IAM resources from Pulumi

## Supersedes

- `docs/plans/2026-03-09-mail-ingest-plan.md` (absorbed into this service)
- `docs/plans/2026-03-09-mail-ingest-replies-plan.md` (absorbed into this service)
- `docs/plans/2026-03-09-mail-ingest-design.md` (absorbed into this service)

The infra plan `docs/plans/mail-plan.md` remains valid -- it provisions the AWS resources this service consumes. The only change is the container image name.

# Data Model v2 Design

## Summary

Rewrite the data model to fix structural issues accumulated from incremental development. Unified `messages` table replaces `inbound_messages` + `replies`. Simplified campaign audience. Body stored in DB. Existing subscribers, lists, tags, and users preserved.

## Problems with v1

1. **Two email tables** (`inbound_messages` + `replies`) that are the same concept. Threading requires cross-table joins and union types.
2. **Campaign audience split** between `listId` (FK) and `audience` (JSON blob). Every query branches on both.
3. **Three different message ID fields** across two tables. Thread matching crosses table boundaries.
4. **fromAddrs/toAddrs stored as JSON strings**, parsed everywhere with a helper.
5. **Email body not stored** -- fetched from S3 and parsed on every view.
6. **Drizzle migration timestamps** generated out of order by subagents, causing silent migration failures in production.

## What stays unchanged

- `users`, `user_lists` -- no changes
- `subscribers` -- no changes (data preserved in migration)
- `subscriber_lists` -- no changes (data preserved)
- `subscriber_tags`, `tags` -- no changes (data preserved)

## New schema

### `campaigns` -- simplified audience

```sql
campaigns:
  id              INTEGER PK
  subject         TEXT NOT NULL
  bodyMarkdown    TEXT NOT NULL
  templateSlug    TEXT NOT NULL DEFAULT 'newsletter'
  fromAddress     TEXT NOT NULL
  audienceType    TEXT NOT NULL  -- 'list' | 'tag' | 'all' | 'subscribers'
  audienceId      INTEGER        -- listId for 'list', tagId for 'tag', null otherwise
  audienceData    TEXT            -- JSON subscriber IDs for 'subscribers' only
  status          TEXT NOT NULL DEFAULT 'draft'  -- draft | sending | sent | failed
  lastError       TEXT
  sentAt          TEXT
  createdAt       TEXT NOT NULL
```

Replaces `listId` + `audience` JSON with three clean fields: `audienceType`, `audienceId`, `audienceData`.

### `campaign_sends` -- no changes

Same structure, FK to campaigns.

### `messages` -- unified email table

```sql
messages:
  id                INTEGER PK
  threadId          INTEGER NOT NULL FK -> messages.id  -- root of this thread (self for root messages)
  parentId          INTEGER FK -> messages.id           -- direct parent, nullable for roots
  direction         TEXT NOT NULL  -- 'inbound' | 'outbound'

  rfc822MessageId   TEXT           -- Message-ID header
  inReplyTo         TEXT           -- In-Reply-To header
  fromAddr          TEXT NOT NULL  -- plain email address
  toAddr            TEXT NOT NULL  -- plain email address
  subject           TEXT NOT NULL

  bodyText          TEXT           -- plain text body
  bodyHtml          TEXT           -- HTML body

  sesMessageId      TEXT UNIQUE    -- SES internal ID (inbound: for dedup, outbound: for tracking)
  s3Key             TEXT           -- S3 key for raw .eml (inbound only)
  spamVerdict       TEXT           -- inbound only
  virusVerdict      TEXT
  spfVerdict        TEXT
  dkimVerdict       TEXT
  dmarcVerdict      TEXT

  campaignId        INTEGER FK -> campaigns.id  -- linked campaign

  readAt            TEXT
  sentAt            TEXT
  createdAt         TEXT NOT NULL
```

### `events` -- updated FK

Replace `inboundMessageId` with `messageId` (FK to messages).

## Thread matching (poller)

When an inbound message arrives:

1. Parse the raw .eml from S3 to extract bodyText/bodyHtml (via mailparser)
2. Check `inReplyTo` against `messages.rfc822MessageId` (covers both inbound and outbound)
3. If match found: `parentId = matchedMessage.id`, `threadId = matchedMessage.threadId`
4. If no match: check campaign linkage (reply-to slug matching)
5. If still no match: new thread, `threadId = self.id` (insert, then update threadId to own id)

## Thread view

```sql
SELECT * FROM messages WHERE threadId = ? ORDER BY createdAt
```

One query. No joins. No union types. Inbound messages have verdicts and s3Key. Outbound messages have those as null.

## Migration strategy

- Create new tables (`messages`, updated `campaigns`)
- Migrate subscriber data: subscribers, subscriber_lists, subscriber_tags, tags, users, user_lists -- copy as-is (these tables don't change)
- Drop old tables: `inbound_messages`, `replies`, old `campaigns`, `campaign_sends`
- Since campaigns/inbound data is expendable, this is a clean rebuild
- Single migration file that creates the new schema from scratch

Actually, since we're preserving subscribers but dropping campaigns/messages, the cleanest approach:
1. Drop `events`, `replies`, `inbound_messages`, `campaign_sends`, `campaigns`
2. Create new `campaigns`, `campaign_sends`, `messages`, `events` tables
3. Subscribers/lists/tags/users tables untouched

## Drizzle migration fix

Going forward: after every `drizzle-kit generate`, verify the `when` timestamp in `_journal.json` is strictly increasing. Add a CI check or pre-commit hook.

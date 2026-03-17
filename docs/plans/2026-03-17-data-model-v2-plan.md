# Data Model v2 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rewrite the data model with a unified messages table, simplified campaign audience, and stored email bodies. Preserve subscriber/list/tag/user data.

**Architecture:** New schema replaces `inbound_messages` + `replies` with unified `messages` table. Campaign audience collapses `listId` + `audience` JSON into typed fields. Poller parses email bodies on ingest. Thread view is one query.

**Tech Stack:** Drizzle ORM (SQLite), mailparser, existing Bun/Hono stack.

**Design doc:** `docs/plans/2026-03-17-data-model-v2-design.md`

**IMPORTANT:** After every `drizzle-kit generate`, verify the `when` timestamp in `drizzle/meta/_journal.json` is strictly greater than the previous entry. Fix if not.

---

### Task 1: New schema

**Files:**
- Rewrite: `src/db/schema.ts`
- Migration: `drizzle/`

**Step 1:** Rewrite schema.ts with:

- `users`, `subscribers`, `lists`, `userLists`, `subscriberLists`, `tags`, `subscriberTags` -- unchanged
- `campaigns` -- replace `listId` + `audience` with `audienceType`, `audienceId`, `audienceData`
- `campaignSends` -- unchanged structure
- `messages` -- new unified table per design doc
- `events` -- replace `inboundMessageId` with `messageId`

**Step 2:** Write migration `drizzle/0013_data-model-v2.sql` manually:

```sql
-- Drop old tables (order matters for FK constraints)
DROP TABLE IF EXISTS events;
DROP TABLE IF EXISTS replies;
DROP TABLE IF EXISTS inbound_messages;
DROP TABLE IF EXISTS campaign_sends;
DROP TABLE IF EXISTS campaigns;

-- Create new campaigns table
CREATE TABLE campaigns (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  subject TEXT NOT NULL,
  body_markdown TEXT NOT NULL,
  template_slug TEXT NOT NULL DEFAULT 'newsletter',
  from_address TEXT NOT NULL,
  audience_type TEXT NOT NULL,
  audience_id INTEGER,
  audience_data TEXT,
  status TEXT NOT NULL DEFAULT 'draft',
  last_error TEXT,
  sent_at TEXT,
  created_at TEXT NOT NULL
);

-- Create new campaign_sends table
CREATE TABLE campaign_sends (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  campaign_id INTEGER NOT NULL REFERENCES campaigns(id),
  subscriber_id INTEGER NOT NULL REFERENCES subscribers(id),
  ses_message_id TEXT,
  status TEXT NOT NULL DEFAULT 'pending',
  sent_at TEXT
);

-- Create new messages table
CREATE TABLE messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  thread_id INTEGER NOT NULL,
  parent_id INTEGER,
  direction TEXT NOT NULL,
  rfc822_message_id TEXT,
  in_reply_to TEXT,
  from_addr TEXT NOT NULL,
  to_addr TEXT NOT NULL,
  subject TEXT NOT NULL,
  body_text TEXT,
  body_html TEXT,
  ses_message_id TEXT UNIQUE,
  s3_key TEXT,
  spam_verdict TEXT,
  virus_verdict TEXT,
  spf_verdict TEXT,
  dkim_verdict TEXT,
  dmarc_verdict TEXT,
  campaign_id INTEGER REFERENCES campaigns(id),
  read_at TEXT,
  sent_at TEXT,
  created_at TEXT NOT NULL
);

-- Create new events table
CREATE TABLE events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  type TEXT NOT NULL,
  detail TEXT NOT NULL DEFAULT '',
  meta TEXT,
  user_id INTEGER REFERENCES users(id),
  subscriber_id INTEGER REFERENCES subscribers(id),
  campaign_id INTEGER REFERENCES campaigns(id),
  message_id INTEGER REFERENCES messages(id),
  created_at TEXT NOT NULL
);
```

**Step 3:** Update `drizzle/meta/_journal.json` -- add entry with idx 13 and a `when` timestamp AFTER the previous entry. Verify ordering.

**Step 4:** Run `bun test` -- many tests will fail (expected, old schema references). Just verify the app starts and migrations run.

**Step 5:** Commit.

---

### Task 2: Update sender service

**Files:**
- Rewrite: `src/services/sender.ts`

**Step 1:** Replace audience resolution. Instead of branching on `listId ?? audience`:

```typescript
if (campaign.audienceType === "list") {
  subscribers = getConfirmedSubscribers(db, campaign.audienceId!);
} else if (campaign.audienceType === "tag") {
  subscribers = getSubscribersByTag(db, campaign.audienceId!);
} else if (campaign.audienceType === "subscribers") {
  const ids = JSON.parse(campaign.audienceData!) as number[];
  subscribers = getSubscribersByIds(db, ids);
} else { // "all"
  subscribers = getAllActiveConfirmedSubscribers(db);
}
```

**Step 2:** When sending, after SES returns, create a `messages` row for each sent email (direction: "outbound") with the `rfc822MessageId` we generated, `sesMessageId` from SES, `campaignId`, and `bodyHtml`/`bodyText` from the render. Set `threadId` to self (the campaign send is the root of the thread).

Actually -- campaign sends don't need to be in the messages table. They're tracked in `campaignSends`. The `messages` table is for conversational email (inbound + admin replies). Campaign sends start threads that inbound messages then join.

Revised: don't put campaign sends in messages. But DO store the campaign's `rfc822MessageId` per subscriber in `campaignSends` so inbound messages can thread back to them. Add `rfc822MessageId` to `campaignSends`.

Actually even simpler: the `messages` table already has `campaignId`. When an inbound arrives with `inReplyTo` matching a campaign send's SES Message-ID, we link via `campaignId` and the thread starts from that inbound message.

Keep sender as-is but simplified for the new audience fields.

**Step 3:** Run `bun test`, commit.

---

### Task 3: Update poller service

**Files:**
- Rewrite: `src/services/poller.ts`

**Step 1:** When processing an SQS message:
- Fetch the raw .eml from S3
- Parse with `simpleParser` to extract `bodyText`, `bodyHtml`, `from`, `to`
- Parse `inReplyTo`, `references` from the parsed email (more reliable than Lambda payload)

**Step 2:** Thread matching:
- Check `inReplyTo` against `messages.rfc822MessageId` (any direction)
- If match: `parentId = match.id`, `threadId = match.threadId`
- If no match: check campaign linkage (reply-to slug matching, same as before)
- If new thread: insert with `threadId = 0`, then update `threadId = self.id`

**Step 3:** Insert into `messages` table with direction "inbound", all fields populated.

**Step 4:** Run `bun test`, commit.

---

### Task 4: Update admin routes -- campaigns

**Files:**
- Modify: `src/routes/admin.tsx`

**Step 1:** Campaign creation: the audience selector already POSTs `audienceMode`. Map to new fields:
- `audienceMode === "list"` → `audienceType: "list", audienceId: listId`
- `audienceMode === "tag"` → `audienceType: "tag", audienceId: tagId`
- `audienceMode === "all"` → `audienceType: "all"`
- `audienceMode === "specific"` → `audienceType: "subscribers", audienceData: JSON.stringify(ids)`

**Step 2:** Campaign display: `describeAudience` helper uses `audienceType`/`audienceId` instead of branching on `listId`/`audience`.

**Step 3:** Campaign detail, edit, preview -- update all queries for new schema.

**Step 4:** Run `bun test`, commit.

---

### Task 5: Update admin routes -- messages (was inbound)

**Files:**
- Modify: `src/routes/admin.tsx`

**Step 1:** Replace all `inboundMessages` references with `messages` table. Filter by `direction = "inbound"` where needed for the list page.

**Step 2:** Thread view: `SELECT * FROM messages WHERE threadId = ? ORDER BY createdAt`. One query, render each message as a card (inbound = white, outbound = blue).

**Step 3:** Reply form: creates a new `messages` row with direction "outbound", `parentId` and `threadId` set from the thread, sends via SES, stores `sesMessageId` and `rfc822MessageId`.

**Step 4:** Inbound list page: group by thread (show one row per thread with latest message date, reply count).

**Step 5:** Run `bun test`, commit.

---

### Task 6: Update remaining code

**Files:**
- Modify: `src/routes/public.tsx` (unsubscribe routes reference campaigns)
- Modify: `src/routes/api.ts` (campaign send endpoint)
- Modify: `src/services/events.ts` (messageId instead of inboundMessageId)
- Modify: `src/compliance.ts` (if any changes needed)
- Modify: `src/bootstrap.ts` (if any changes needed)

**Step 1:** Update all imports and references to match new schema names.

**Step 2:** Run `bun test`, commit.

---

### Task 7: Update all tests

**Files:**
- Rewrite: `tests/e2e.test.ts`
- Rewrite: `tests/subscriber.test.ts` (minor -- subscriber tests shouldn't need big changes)
- Modify: `tests/helpers.ts`
- Modify: `tests/sender.test.ts`
- Modify: `tests/auth.test.ts`
- Modify: `tests/users.test.ts`

**Step 1:** Update all test helpers and fixtures for new schema.

**Step 2:** Rewrite e2e tests for:
- Campaign send (new audience fields)
- Message threading (unified table)
- Preview endpoints
- Subscribe + confirm flow

**Step 3:** Run `bun test` -- all must pass.

**Step 4:** Commit.

---

### Task 8: Final verification

**Step 1:** Run `bun test`
**Step 2:** `bun run build:css`
**Step 3:** `docker build -t lists:test .`
**Step 4:** Smoke test locally
**Step 5:** Push both repos

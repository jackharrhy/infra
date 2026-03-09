# `lists` Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a personal newsletter service that handles subscriber management (independent topic lists), campaign sending via SES API, inbound reply tracking via SQS, and email compliance -- replacing listmonk.

**Architecture:** Single Bun process with Hono HTTP server + background SQS poller. Drizzle ORM on bun:sqlite for persistence. React-email for rendering campaign templates. Hono JSX for server-rendered admin UI and public pages.

**Tech Stack:** Bun, Hono, Drizzle ORM (bun:sqlite), react-email, AWS SDK v3 (SES/SQS/S3), marked (markdown)

**Design doc:** `docs/plans/2026-03-09-lists-design.md`

**Repo:** `jackharrhy/lists` (empty, already created)

**Env vars:**

| Var | Purpose |
|-----|---------|
| `AWS_ACCESS_KEY_ID` | IAM credentials (SES + SQS + S3) |
| `AWS_SECRET_ACCESS_KEY` | IAM credentials |
| `AWS_REGION` | `us-east-1` |
| `SQS_QUEUE_URL` | Inbound email queue |
| `S3_BUCKET` | Raw .eml storage |
| `AUTH_PASSWORD` | Admin UI password |
| `API_TOKEN` | Bearer token for API |
| `DB_PATH` | SQLite path (default: `/data/lists.db`) |
| `FROM_DOMAIN` | `jackharrhy.dev` |
| `BASE_URL` | `https://lists.jackharrhy.dev` |

---

### Task 1: Scaffold the project

**Files:**
- Create: `package.json`
- Create: `tsconfig.json`
- Create: `drizzle.config.ts`
- Create: `src/index.ts`
- Create: `src/config.ts`
- Create: `Dockerfile`
- Create: `.github/workflows/build.yml`
- Create: `.gitignore`

**Step 1: Initialize the project**

Run: `bun init`

**Step 2: Install dependencies**

Run:
```bash
bun add hono @hono/node-server drizzle-orm @react-email/components @react-email/render marked
bun add -d drizzle-kit @types/bun typescript
bun add @aws-sdk/client-ses @aws-sdk/client-sqs @aws-sdk/client-s3 @aws-sdk/s3-request-presigner
```

**Step 3: Create `tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ESNext",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "jsxImportSource": "hono/jsx",
    "strict": true,
    "esModuleInterop": true,
    "outDir": "./dist",
    "rootDir": "./src",
    "types": ["bun-types"]
  },
  "include": ["src/**/*", "emails/**/*"]
}
```

**Step 4: Create `src/config.ts`**

```typescript
export type Config = {
  awsRegion: string;
  sqsQueueUrl: string;
  s3Bucket: string;
  authPassword: string;
  apiToken: string;
  dbPath: string;
  fromDomain: string;
  baseUrl: string;
};

export function loadConfig(): Config {
  const required = (key: string): string => {
    const val = process.env[key];
    if (!val) throw new Error(`${key} is required`);
    return val;
  };

  return {
    awsRegion: process.env.AWS_REGION ?? "us-east-1",
    sqsQueueUrl: required("SQS_QUEUE_URL"),
    s3Bucket: required("S3_BUCKET"),
    authPassword: required("AUTH_PASSWORD"),
    apiToken: required("API_TOKEN"),
    dbPath: process.env.DB_PATH ?? "lists.db",
    fromDomain: process.env.FROM_DOMAIN ?? "jackharrhy.dev",
    baseUrl: required("BASE_URL"),
  };
}
```

**Step 5: Create `src/index.ts` stub**

```typescript
import { Hono } from "hono";
import { loadConfig } from "./config";

const config = loadConfig();

const app = new Hono();

app.get("/", (c) => c.text("lists"));

export default {
  port: 8080,
  fetch: app.fetch,
};
```

**Step 6: Create `drizzle.config.ts`**

```typescript
import { defineConfig } from "drizzle-kit";

export default defineConfig({
  schema: "./src/db/schema.ts",
  out: "./drizzle",
  dialect: "sqlite",
});
```

**Step 7: Create `.gitignore`**

```
node_modules/
dist/
*.db
.env
```

**Step 8: Create `Dockerfile`**

```dockerfile
FROM oven/bun:1 AS build
WORKDIR /app
COPY package.json bun.lockb ./
RUN bun install --frozen-lockfile
COPY . .

FROM oven/bun:1
WORKDIR /app
COPY --from=build /app /app
ENV DB_PATH=/data/lists.db
VOLUME /data
EXPOSE 8080
CMD ["bun", "run", "src/index.ts"]
```

**Step 9: Create `.github/workflows/build.yml`**

```yaml
name: Build and Push

on:
  push:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4

      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push
        uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:main
```

**Step 10: Verify it runs**

Run: `SQS_QUEUE_URL=fake S3_BUCKET=fake AUTH_PASSWORD=test API_TOKEN=test BASE_URL=http://localhost:8080 bun run src/index.ts`
Expected: Server starts on :8080, `curl http://localhost:8080` returns "lists".

**Step 11: Commit**

```bash
git add -A
git commit -m "feat: scaffold lists project"
```

---

### Task 2: Database schema and migrations

**Files:**
- Create: `src/db/schema.ts`
- Create: `src/db/index.ts`

**Step 1: Define the Drizzle schema**

`src/db/schema.ts`:

```typescript
import { sqliteTable, text, integer } from "drizzle-orm/sqlite-core";

export const subscribers = sqliteTable("subscribers", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  email: text("email").notNull().unique(),
  name: text("name"),
  status: text("status", { enum: ["active", "unsubscribed", "blocklisted"] })
    .notNull()
    .default("active"),
  unsubscribeToken: text("unsubscribe_token").notNull().unique(),
  createdAt: text("created_at")
    .notNull()
    .$defaultFn(() => new Date().toISOString()),
  confirmedAt: text("confirmed_at"),
});

export const lists = sqliteTable("lists", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  slug: text("slug").notNull().unique(),
  name: text("name").notNull(),
  description: text("description").notNull().default(""),
});

export const subscriberLists = sqliteTable("subscriber_lists", {
  subscriberId: integer("subscriber_id")
    .notNull()
    .references(() => subscribers.id),
  listId: integer("list_id")
    .notNull()
    .references(() => lists.id),
  status: text("status", {
    enum: ["unconfirmed", "confirmed", "unsubscribed"],
  })
    .notNull()
    .default("unconfirmed"),
  subscribedAt: text("subscribed_at")
    .notNull()
    .$defaultFn(() => new Date().toISOString()),
});

export const campaigns = sqliteTable("campaigns", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  listId: integer("list_id")
    .notNull()
    .references(() => lists.id),
  subject: text("subject").notNull(),
  bodyMarkdown: text("body_markdown").notNull(),
  templateSlug: text("template_slug").notNull().default("newsletter"),
  fromAddress: text("from_address").notNull(),
  status: text("status", { enum: ["draft", "sending", "sent"] })
    .notNull()
    .default("draft"),
  sentAt: text("sent_at"),
  createdAt: text("created_at")
    .notNull()
    .$defaultFn(() => new Date().toISOString()),
});

export const campaignSends = sqliteTable("campaign_sends", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  campaignId: integer("campaign_id")
    .notNull()
    .references(() => campaigns.id),
  subscriberId: integer("subscriber_id")
    .notNull()
    .references(() => subscribers.id),
  sesMessageId: text("ses_message_id"),
  status: text("status", { enum: ["pending", "sent", "bounced"] })
    .notNull()
    .default("pending"),
  sentAt: text("sent_at"),
});

export const inboundMessages = sqliteTable("inbound_messages", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  messageId: text("message_id").notNull().unique(),
  timestamp: text("timestamp").notNull(),
  source: text("source").notNull(),
  fromAddrs: text("from_addrs").notNull(),
  toAddrs: text("to_addrs").notNull(),
  subject: text("subject").notNull(),
  spamVerdict: text("spam_verdict"),
  virusVerdict: text("virus_verdict"),
  spfVerdict: text("spf_verdict"),
  dkimVerdict: text("dkim_verdict"),
  dmarcVerdict: text("dmarc_verdict"),
  s3Key: text("s3_key"),
  campaignId: integer("campaign_id").references(() => campaigns.id),
  createdAt: text("created_at")
    .notNull()
    .$defaultFn(() => new Date().toISOString()),
});

export const replies = sqliteTable("replies", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  inboundMessageId: integer("inbound_message_id")
    .notNull()
    .references(() => inboundMessages.id),
  fromAddr: text("from_addr").notNull(),
  toAddr: text("to_addr").notNull(),
  subject: text("subject").notNull(),
  body: text("body").notNull(),
  sesMessageId: text("ses_message_id"),
  inReplyTo: text("in_reply_to"),
  sentAt: text("sent_at")
    .notNull()
    .$defaultFn(() => new Date().toISOString()),
});
```

**Step 2: Create `src/db/index.ts`**

```typescript
import { drizzle } from "drizzle-orm/bun-sqlite";
import { migrate } from "drizzle-orm/bun-sqlite/migrator";
import * as schema from "./schema";

export function createDb(dbPath: string) {
  const db = drizzle(dbPath, { schema });
  migrate(db, { migrationsFolder: "./drizzle" });
  return db;
}

export type Db = ReturnType<typeof createDb>;
export { schema };
```

**Step 3: Generate the initial migration**

Run: `bunx drizzle-kit generate --name=init`
Expected: Creates `drizzle/0000_init.sql` with all CREATE TABLE statements.

**Step 4: Verify it works**

Update `src/index.ts` to create the DB:

```typescript
import { Hono } from "hono";
import { loadConfig } from "./config";
import { createDb } from "./db";

const config = loadConfig();
const db = createDb(config.dbPath);

const app = new Hono();

app.get("/", (c) => c.text("lists"));

export default {
  port: 8080,
  fetch: app.fetch,
};
```

Run: `SQS_QUEUE_URL=fake S3_BUCKET=fake AUTH_PASSWORD=test API_TOKEN=test BASE_URL=http://localhost:8080 DB_PATH=./test.db bun run src/index.ts`
Expected: Starts without errors, `test.db` is created with tables.

Run: `rm test.db`

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: add database schema and migrations"
```

---

### Task 3: Compliance utilities

**Files:**
- Create: `src/compliance.ts`

**Step 1: Implement token generation and unsubscribe header building**

```typescript
import { randomBytes } from "crypto";

export function generateToken(): string {
  return randomBytes(32).toString("hex");
}

export function buildUnsubscribeUrl(baseUrl: string, token: string): string {
  return `${baseUrl}/unsubscribe/${token}`;
}

export function buildPreferencesUrl(baseUrl: string, token: string): string {
  return `${baseUrl}/preferences/${token}`;
}

export function buildListUnsubscribeHeader(
  unsubscribeUrl: string,
): Record<string, string> {
  return {
    "List-Unsubscribe": `<${unsubscribeUrl}>`,
    "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
  };
}
```

**Step 2: Commit**

```bash
git add src/compliance.ts
git commit -m "feat: add compliance utilities (tokens, unsubscribe headers)"
```

---

### Task 4: Subscriber service

**Files:**
- Create: `src/services/subscriber.ts`

**Step 1: Implement subscriber management logic**

```typescript
import { eq, and } from "drizzle-orm";
import type { Db } from "../db";
import { schema } from "../db";
import { generateToken } from "../compliance";

export async function createSubscriber(
  db: Db,
  email: string,
  name: string | null,
  listSlugs: string[],
) {
  const normalizedEmail = email.toLowerCase().trim();

  // Find or create subscriber
  let subscriber = db
    .select()
    .from(schema.subscribers)
    .where(eq(schema.subscribers.email, normalizedEmail))
    .get();

  if (!subscriber) {
    const result = db
      .insert(schema.subscribers)
      .values({
        email: normalizedEmail,
        name,
        unsubscribeToken: generateToken(),
      })
      .returning()
      .get();
    subscriber = result;
  }

  // Subscribe to requested lists
  const allLists = db.select().from(schema.lists).all();
  for (const slug of listSlugs) {
    const list = allLists.find((l) => l.slug === slug);
    if (!list) continue;

    const existing = db
      .select()
      .from(schema.subscriberLists)
      .where(
        and(
          eq(schema.subscriberLists.subscriberId, subscriber.id),
          eq(schema.subscriberLists.listId, list.id),
        ),
      )
      .get();

    if (!existing) {
      db.insert(schema.subscriberLists)
        .values({
          subscriberId: subscriber.id,
          listId: list.id,
          status: "unconfirmed",
        })
        .run();
    }
  }

  return subscriber;
}

export function confirmSubscriber(db: Db, token: string): boolean {
  const subscriber = db
    .select()
    .from(schema.subscribers)
    .where(eq(schema.subscribers.unsubscribeToken, token))
    .get();

  if (!subscriber) return false;

  db.update(schema.subscribers)
    .set({ confirmedAt: new Date().toISOString() })
    .where(eq(schema.subscribers.id, subscriber.id))
    .run();

  db.update(schema.subscriberLists)
    .set({ status: "confirmed" })
    .where(
      and(
        eq(schema.subscriberLists.subscriberId, subscriber.id),
        eq(schema.subscriberLists.status, "unconfirmed"),
      ),
    )
    .run();

  return true;
}

export function unsubscribeAll(db: Db, token: string): boolean {
  const subscriber = db
    .select()
    .from(schema.subscribers)
    .where(eq(schema.subscribers.unsubscribeToken, token))
    .get();

  if (!subscriber) return false;

  db.update(schema.subscribers)
    .set({ status: "unsubscribed" })
    .where(eq(schema.subscribers.id, subscriber.id))
    .run();

  db.update(schema.subscriberLists)
    .set({ status: "unsubscribed" })
    .where(eq(schema.subscriberLists.subscriberId, subscriber.id))
    .run();

  return true;
}

export function getSubscriberPreferences(db: Db, token: string) {
  const subscriber = db
    .select()
    .from(schema.subscribers)
    .where(eq(schema.subscribers.unsubscribeToken, token))
    .get();

  if (!subscriber) return null;

  const allLists = db.select().from(schema.lists).all();
  const subscriptions = db
    .select()
    .from(schema.subscriberLists)
    .where(eq(schema.subscriberLists.subscriberId, subscriber.id))
    .all();

  return {
    subscriber,
    lists: allLists.map((list) => ({
      ...list,
      status:
        subscriptions.find((s) => s.listId === list.id)?.status ?? "none",
    })),
  };
}

export function updatePreferences(
  db: Db,
  token: string,
  subscribedListIds: number[],
) {
  const subscriber = db
    .select()
    .from(schema.subscribers)
    .where(eq(schema.subscribers.unsubscribeToken, token))
    .get();

  if (!subscriber) return false;

  const allLists = db.select().from(schema.lists).all();

  for (const list of allLists) {
    const shouldBeSubscribed = subscribedListIds.includes(list.id);
    const existing = db
      .select()
      .from(schema.subscriberLists)
      .where(
        and(
          eq(schema.subscriberLists.subscriberId, subscriber.id),
          eq(schema.subscriberLists.listId, list.id),
        ),
      )
      .get();

    if (shouldBeSubscribed && !existing) {
      db.insert(schema.subscriberLists)
        .values({
          subscriberId: subscriber.id,
          listId: list.id,
          status: "confirmed",
        })
        .run();
    } else if (shouldBeSubscribed && existing?.status === "unsubscribed") {
      db.update(schema.subscriberLists)
        .set({ status: "confirmed" })
        .where(
          and(
            eq(schema.subscriberLists.subscriberId, subscriber.id),
            eq(schema.subscriberLists.listId, list.id),
          ),
        )
        .run();
    } else if (!shouldBeSubscribed && existing) {
      db.update(schema.subscriberLists)
        .set({ status: "unsubscribed" })
        .where(
          and(
            eq(schema.subscriberLists.subscriberId, subscriber.id),
            eq(schema.subscriberLists.listId, list.id),
          ),
        )
        .run();
    }
  }

  return true;
}

export function getConfirmedSubscribers(db: Db, listId: number) {
  return db
    .select({
      id: schema.subscribers.id,
      email: schema.subscribers.email,
      name: schema.subscribers.name,
      unsubscribeToken: schema.subscribers.unsubscribeToken,
    })
    .from(schema.subscribers)
    .innerJoin(
      schema.subscriberLists,
      eq(schema.subscriberLists.subscriberId, schema.subscribers.id),
    )
    .where(
      and(
        eq(schema.subscriberLists.listId, listId),
        eq(schema.subscriberLists.status, "confirmed"),
        eq(schema.subscribers.status, "active"),
      ),
    )
    .all();
}
```

**Step 2: Verify it compiles**

Run: `bun build src/index.ts --target=bun --outdir=dist`
Expected: No errors.

**Step 3: Commit**

```bash
git add src/services/subscriber.ts
git commit -m "feat: add subscriber management service"
```

---

### Task 5: React-email templates

**Files:**
- Create: `emails/templates/newsletter.tsx`
- Create: `emails/templates/confirm.tsx`
- Create: `emails/components/footer.tsx`
- Create: `emails/render.ts`

**Step 1: Create shared footer component**

`emails/components/footer.tsx`:

```tsx
import { Hr, Link, Text } from "@react-email/components";

type FooterProps = {
  unsubscribeUrl: string;
  preferencesUrl: string;
};

export function Footer({ unsubscribeUrl, preferencesUrl }: FooterProps) {
  return (
    <>
      <Hr style={{ borderColor: "#e5e5e5", margin: "24px 0" }} />
      <Text style={{ color: "#666", fontSize: "12px", lineHeight: "20px" }}>
        <Link href={preferencesUrl} style={{ color: "#666" }}>
          Manage preferences
        </Link>
        {" | "}
        <Link href={unsubscribeUrl} style={{ color: "#666" }}>
          Unsubscribe
        </Link>
      </Text>
    </>
  );
}
```

**Step 2: Create newsletter template**

`emails/templates/newsletter.tsx`:

```tsx
import {
  Body,
  Container,
  Head,
  Html,
  Preview,
  Section,
  Text,
} from "@react-email/components";
import { Footer } from "../components/footer";

type NewsletterProps = {
  subject: string;
  contentHtml: string;
  listName: string;
  unsubscribeUrl: string;
  preferencesUrl: string;
};

export function Newsletter({
  subject,
  contentHtml,
  listName,
  unsubscribeUrl,
  preferencesUrl,
}: NewsletterProps) {
  return (
    <Html>
      <Head />
      <Preview>{subject}</Preview>
      <Body style={{ backgroundColor: "#ffffff", fontFamily: "system-ui, sans-serif" }}>
        <Container style={{ maxWidth: "600px", margin: "0 auto", padding: "20px" }}>
          <Text style={{ fontSize: "12px", color: "#999", textTransform: "uppercase" }}>
            {listName}
          </Text>
          <Section dangerouslySetInnerHTML={{ __html: contentHtml }} />
          <Footer
            unsubscribeUrl={unsubscribeUrl}
            preferencesUrl={preferencesUrl}
          />
        </Container>
      </Body>
    </Html>
  );
}
```

**Step 3: Create confirmation template**

`emails/templates/confirm.tsx`:

```tsx
import {
  Body,
  Button,
  Container,
  Head,
  Html,
  Preview,
  Text,
} from "@react-email/components";

type ConfirmProps = {
  confirmUrl: string;
  listNames: string[];
};

export function Confirm({ confirmUrl, listNames }: ConfirmProps) {
  return (
    <Html>
      <Head />
      <Preview>Confirm your subscription</Preview>
      <Body style={{ backgroundColor: "#ffffff", fontFamily: "system-ui, sans-serif" }}>
        <Container style={{ maxWidth: "600px", margin: "0 auto", padding: "20px" }}>
          <Text style={{ fontSize: "18px", fontWeight: "bold" }}>
            Confirm your subscription
          </Text>
          <Text>
            You&apos;re subscribing to: {listNames.join(", ")}
          </Text>
          <Button
            href={confirmUrl}
            style={{
              backgroundColor: "#000",
              color: "#fff",
              padding: "12px 24px",
              borderRadius: "4px",
              textDecoration: "none",
            }}
          >
            Confirm subscription
          </Button>
          <Text style={{ color: "#666", fontSize: "14px" }}>
            If you didn&apos;t request this, you can safely ignore this email.
          </Text>
        </Container>
      </Body>
    </Html>
  );
}
```

**Step 4: Create render utility**

`emails/render.ts`:

```typescript
import { render } from "@react-email/render";
import { Newsletter } from "./templates/newsletter";
import { Confirm } from "./templates/confirm";

export async function renderNewsletter(props: {
  subject: string;
  contentHtml: string;
  listName: string;
  unsubscribeUrl: string;
  preferencesUrl: string;
}) {
  const html = await render(Newsletter(props));
  return { html };
}

export async function renderConfirmation(props: {
  confirmUrl: string;
  listNames: string[];
}) {
  const html = await render(Confirm(props));
  return { html };
}
```

**Step 5: Verify it compiles**

Run: `bun build src/index.ts --target=bun --outdir=dist`
Expected: No errors.

**Step 6: Commit**

```bash
git add emails/
git commit -m "feat: add react-email templates (newsletter, confirmation)"
```

---

### Task 6: Campaign sender service

**Files:**
- Create: `src/services/sender.ts`

**Step 1: Implement campaign sending**

```typescript
import {
  SESv2Client,
  SendEmailCommand,
} from "@aws-sdk/client-sesv2";
import { eq, and } from "drizzle-orm";
import { marked } from "marked";
import type { Config } from "../config";
import type { Db } from "../db";
import { schema } from "../db";
import { getConfirmedSubscribers } from "./subscriber";
import {
  buildUnsubscribeUrl,
  buildPreferencesUrl,
  buildListUnsubscribeHeader,
} from "../compliance";
import { renderNewsletter } from "../../emails/render";

function buildRawEmail(opts: {
  from: string;
  to: string;
  subject: string;
  html: string;
  headers: Record<string, string>;
}): Uint8Array {
  const boundary = `----=${Date.now()}`;
  const lines = [
    `From: ${opts.from}`,
    `To: ${opts.to}`,
    `Subject: ${opts.subject}`,
    `MIME-Version: 1.0`,
    ...Object.entries(opts.headers).map(([k, v]) => `${k}: ${v}`),
    `Content-Type: multipart/alternative; boundary="${boundary}"`,
    ``,
    `--${boundary}`,
    `Content-Type: text/html; charset=UTF-8`,
    `Content-Transfer-Encoding: 7bit`,
    ``,
    opts.html,
    ``,
    `--${boundary}--`,
  ];
  return new TextEncoder().encode(lines.join("\r\n"));
}

export async function sendCampaign(db: Db, config: Config, campaignId: number) {
  const campaign = db
    .select()
    .from(schema.campaigns)
    .where(eq(schema.campaigns.id, campaignId))
    .get();

  if (!campaign || campaign.status !== "draft") {
    throw new Error("Campaign not found or not in draft status");
  }

  const list = db
    .select()
    .from(schema.lists)
    .where(eq(schema.lists.id, campaign.listId))
    .get();

  if (!list) throw new Error("List not found");

  // Mark as sending
  db.update(schema.campaigns)
    .set({ status: "sending" })
    .where(eq(schema.campaigns.id, campaignId))
    .run();

  const subscribers = getConfirmedSubscribers(db, list.id);
  const contentHtml = await marked(campaign.bodyMarkdown);
  const ses = new SESv2Client({ region: config.awsRegion });

  let sentCount = 0;

  for (const subscriber of subscribers) {
    const unsubUrl = buildUnsubscribeUrl(
      config.baseUrl,
      subscriber.unsubscribeToken,
    );
    const prefsUrl = buildPreferencesUrl(
      config.baseUrl,
      subscriber.unsubscribeToken,
    );

    const { html } = await renderNewsletter({
      subject: campaign.subject,
      contentHtml,
      listName: list.name,
      unsubscribeUrl: unsubUrl,
      preferencesUrl: prefsUrl,
    });

    const unsubHeaders = buildListUnsubscribeHeader(unsubUrl);

    try {
      const result = await ses.send(
        new SendEmailCommand({
          Content: {
            Raw: {
              Data: buildRawEmail({
                from: campaign.fromAddress,
                to: subscriber.email,
                subject: campaign.subject,
                html,
                headers: {
                  ...unsubHeaders,
                  "Reply-To": `${list.slug}@reply.${config.fromDomain}`,
                },
              }),
            },
          },
        }),
      );

      db.insert(schema.campaignSends)
        .values({
          campaignId,
          subscriberId: subscriber.id,
          sesMessageId: result.MessageId,
          status: "sent",
          sentAt: new Date().toISOString(),
        })
        .run();

      sentCount++;
    } catch (err) {
      console.error(`Failed to send to ${subscriber.email}:`, err);
      db.insert(schema.campaignSends)
        .values({
          campaignId,
          subscriberId: subscriber.id,
          status: "bounced",
        })
        .run();
    }
  }

  // Mark as sent
  db.update(schema.campaigns)
    .set({ status: "sent", sentAt: new Date().toISOString() })
    .where(eq(schema.campaigns.id, campaignId))
    .run();

  console.log(
    `Campaign ${campaignId} sent to ${sentCount}/${subscribers.length} subscribers`,
  );
}
```

**Step 2: Verify it compiles**

Run: `bun build src/index.ts --target=bun --outdir=dist`
Expected: No errors.

**Step 3: Commit**

```bash
git add src/services/sender.ts
git commit -m "feat: add campaign sender service (SES raw email)"
```

---

### Task 7: SQS poller for inbound email

**Files:**
- Create: `src/services/poller.ts`

**Step 1: Implement the SQS poll loop**

```typescript
import {
  SQSClient,
  ReceiveMessageCommand,
  DeleteMessageCommand,
} from "@aws-sdk/client-sqs";
import { eq } from "drizzle-orm";
import type { Config } from "../config";
import type { Db } from "../db";
import { schema } from "../db";

type SQSPayload = {
  messageId: string;
  timestamp: string;
  source: string;
  from: string[];
  to: string[];
  subject: string;
  spamVerdict: string;
  virusVerdict: string;
  spfVerdict: string;
  dkimVerdict: string;
  dmarcVerdict: string;
  action: {
    type: string;
    bucketName: string;
    objectKeyPrefix: string;
    objectKey: string;
  };
};

export async function startPoller(db: Db, config: Config) {
  const sqs = new SQSClient({ region: config.awsRegion });
  console.log(`Polling SQS queue: ${config.sqsQueueUrl}`);

  while (true) {
    try {
      const result = await sqs.send(
        new ReceiveMessageCommand({
          QueueUrl: config.sqsQueueUrl,
          MaxNumberOfMessages: 10,
          WaitTimeSeconds: 20,
        }),
      );

      for (const msg of result.Messages ?? []) {
        try {
          const payload: SQSPayload = JSON.parse(msg.Body ?? "{}");

          const s3Key =
            payload.action.objectKey ||
            payload.action.objectKeyPrefix + payload.messageId;

          db.insert(schema.inboundMessages)
            .values({
              messageId: payload.messageId,
              timestamp: payload.timestamp,
              source: payload.source,
              fromAddrs: JSON.stringify(payload.from),
              toAddrs: JSON.stringify(payload.to),
              subject: payload.subject,
              spamVerdict: payload.spamVerdict || null,
              virusVerdict: payload.virusVerdict || null,
              spfVerdict: payload.spfVerdict || null,
              dkimVerdict: payload.dkimVerdict || null,
              dmarcVerdict: payload.dmarcVerdict || null,
              s3Key,
            })
            .onConflictDoNothing()
            .run();

          console.log(
            `Stored inbound message ${payload.messageId} from ${payload.from.join(", ")}`,
          );

          await sqs.send(
            new DeleteMessageCommand({
              QueueUrl: config.sqsQueueUrl,
              ReceiptHandle: msg.ReceiptHandle,
            }),
          );
        } catch (err) {
          console.error("Failed to process SQS message:", err);
        }
      }
    } catch (err) {
      console.error("SQS receive error:", err);
      await Bun.sleep(5000);
    }
  }
}
```

**Step 2: Commit**

```bash
git add src/services/poller.ts
git commit -m "feat: add SQS poller for inbound email"
```

---

### Task 8: Auth middleware

**Files:**
- Create: `src/auth.ts`

**Step 1: Implement session auth and bearer token middleware**

```typescript
import { getCookie, setCookie, deleteCookie } from "hono/cookie";
import { bearerAuth } from "hono/bearer-auth";
import { createMiddleware } from "hono/factory";

const sessions = new Map<string, number>(); // token -> expiry timestamp

export function createSession(): string {
  const token = crypto.randomUUID();
  sessions.set(token, Date.now() + 24 * 60 * 60 * 1000); // 24h
  return token;
}

export function destroySession(token: string) {
  sessions.delete(token);
}

function isValidSession(token: string): boolean {
  const expiry = sessions.get(token);
  if (!expiry) return false;
  if (Date.now() > expiry) {
    sessions.delete(token);
    return false;
  }
  return true;
}

export function adminAuth(password: string) {
  return createMiddleware(async (c, next) => {
    const session = getCookie(c, "session");
    if (session && isValidSession(session)) {
      return next();
    }
    return c.redirect("/admin/login");
  });
}

export function apiAuth(token: string) {
  return bearerAuth({ token });
}
```

**Step 2: Commit**

```bash
git add src/auth.ts
git commit -m "feat: add auth middleware (session + bearer token)"
```

---

### Task 9: Public routes (subscribe, confirm, unsubscribe)

**Files:**
- Create: `src/routes/public.tsx`

**Step 1: Implement public routes**

```tsx
import { Hono } from "hono";
import type { Db } from "../db";
import { schema } from "../db";
import type { Config } from "../config";
import {
  createSubscriber,
  confirmSubscriber,
  unsubscribeAll,
  getSubscriberPreferences,
  updatePreferences,
} from "../services/subscriber";
import { renderConfirmation } from "../../emails/render";
import { SESv2Client, SendEmailCommand } from "@aws-sdk/client-sesv2";

function Layout({ children }: { children: any }) {
  return (
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>lists</title>
        <style>{`
          * { margin: 0; padding: 0; box-sizing: border-box; }
          body { font-family: system-ui, sans-serif; max-width: 500px; margin: 2rem auto; padding: 0 1rem; }
          h1 { margin-bottom: 1rem; }
          form { display: flex; flex-direction: column; gap: 0.75rem; }
          label { font-weight: 500; }
          input, button { padding: 0.5rem; font-size: 1rem; }
          button { cursor: pointer; background: #000; color: #fff; border: none; border-radius: 4px; }
          .checkbox-group { display: flex; flex-direction: column; gap: 0.5rem; }
          .checkbox-group label { font-weight: normal; display: flex; align-items: center; gap: 0.5rem; }
          .message { padding: 1rem; background: #f0f0f0; border-radius: 4px; }
        `}</style>
      </head>
      <body>{children}</body>
    </html>
  );
}

export function publicRoutes(db: Db, config: Config) {
  const app = new Hono();

  app.get("/subscribe", (c) => {
    const lists = db.select().from(schema.lists).all();
    return c.html(
      <Layout>
        <h1>Subscribe</h1>
        <form method="POST" action="/subscribe">
          <label for="email">Email</label>
          <input type="email" id="email" name="email" required />
          <label for="name">Name (optional)</label>
          <input type="text" id="name" name="name" />
          <div class="checkbox-group">
            <label>Lists:</label>
            {lists.map((list) => (
              <label>
                <input type="checkbox" name="lists" value={list.slug} />
                {list.name}
                {list.description ? ` — ${list.description}` : ""}
              </label>
            ))}
          </div>
          <button type="submit">Subscribe</button>
        </form>
      </Layout>,
    );
  });

  app.post("/subscribe", async (c) => {
    const body = await c.req.parseBody({ all: true });
    const email = body.email as string;
    const name = (body.name as string) || null;
    const listSlugs = Array.isArray(body.lists)
      ? (body.lists as string[])
      : body.lists
        ? [body.lists as string]
        : [];

    if (!email || listSlugs.length === 0) {
      return c.html(
        <Layout>
          <h1>Error</h1>
          <p>Please provide an email and select at least one list.</p>
        </Layout>,
        400,
      );
    }

    const subscriber = createSubscriber(db, email, name, listSlugs);

    // Send confirmation email
    const confirmUrl = `${config.baseUrl}/confirm/${subscriber.unsubscribeToken}`;
    const listNames = listSlugs; // simplification: use slugs as names

    const { html } = await renderConfirmation({ confirmUrl, listNames });

    const ses = new SESv2Client({ region: config.awsRegion });
    await ses.send(
      new SendEmailCommand({
        FromEmailAddress: `noreply@${config.fromDomain}`,
        Destination: { ToAddresses: [email] },
        Content: {
          Simple: {
            Subject: { Data: "Confirm your subscription" },
            Body: { Html: { Data: html } },
          },
        },
      }),
    );

    return c.html(
      <Layout>
        <h1>Check your email</h1>
        <p class="message">
          We sent a confirmation link to <strong>{email}</strong>. Click it to
          confirm your subscription.
        </p>
      </Layout>,
    );
  });

  app.get("/confirm/:token", (c) => {
    const success = confirmSubscriber(db, c.req.param("token"));
    if (!success) {
      return c.html(
        <Layout>
          <h1>Invalid link</h1>
          <p>This confirmation link is invalid or has expired.</p>
        </Layout>,
        404,
      );
    }
    return c.html(
      <Layout>
        <h1>Confirmed!</h1>
        <p class="message">Your subscription is now active.</p>
      </Layout>,
    );
  });

  app.get("/unsubscribe/:token", (c) => {
    const success = unsubscribeAll(db, c.req.param("token"));
    return c.html(
      <Layout>
        <h1>{success ? "Unsubscribed" : "Invalid link"}</h1>
        <p class="message">
          {success
            ? "You have been unsubscribed from all lists."
            : "This link is invalid."}
        </p>
      </Layout>,
    );
  });

  app.post("/unsubscribe/:token", (c) => {
    // RFC 8058 one-click unsubscribe via POST
    unsubscribeAll(db, c.req.param("token"));
    return c.text("Unsubscribed", 200);
  });

  app.get("/preferences/:token", (c) => {
    const prefs = getSubscriberPreferences(db, c.req.param("token"));
    if (!prefs) return c.html(<Layout><h1>Invalid link</h1></Layout>, 404);

    return c.html(
      <Layout>
        <h1>Manage preferences</h1>
        <p>Email: {prefs.subscriber.email}</p>
        <form method="POST">
          <div class="checkbox-group">
            {prefs.lists.map((list) => (
              <label>
                <input
                  type="checkbox"
                  name="lists"
                  value={String(list.id)}
                  checked={list.status === "confirmed"}
                />
                {list.name}
              </label>
            ))}
          </div>
          <button type="submit">Update preferences</button>
        </form>
      </Layout>,
    );
  });

  app.post("/preferences/:token", async (c) => {
    const body = await c.req.parseBody({ all: true });
    const listIds = (
      Array.isArray(body.lists)
        ? (body.lists as string[])
        : body.lists
          ? [body.lists as string]
          : []
    ).map(Number);

    updatePreferences(db, c.req.param("token"), listIds);

    return c.redirect(`/preferences/${c.req.param("token")}`);
  });

  return app;
}
```

**Step 2: Commit**

```bash
git add src/routes/public.tsx
git commit -m "feat: add public routes (subscribe, confirm, unsubscribe, preferences)"
```

---

### Task 10: API routes

**Files:**
- Create: `src/routes/api.ts`

**Step 1: Implement JSON API**

```typescript
import { Hono } from "hono";
import { eq } from "drizzle-orm";
import type { Db } from "../db";
import { schema } from "../db";
import type { Config } from "../config";
import { apiAuth } from "../auth";
import { createSubscriber } from "../services/subscriber";
import { sendCampaign } from "../services/sender";

export function apiRoutes(db: Db, config: Config) {
  const app = new Hono();

  app.use("/*", apiAuth(config.apiToken));

  app.post("/subscribers", async (c) => {
    const { email, name, lists } = await c.req.json<{
      email: string;
      name?: string;
      lists: string[];
    }>();

    if (!email || !lists?.length) {
      return c.json({ error: "email and lists are required" }, 400);
    }

    const subscriber = createSubscriber(db, email, name ?? null, lists);
    return c.json({ id: subscriber.id, email: subscriber.email }, 201);
  });

  app.get("/subscribers", (c) => {
    const subscribers = db.select().from(schema.subscribers).all();
    return c.json(subscribers);
  });

  app.delete("/subscribers/:id", (c) => {
    const id = Number(c.req.param("id"));
    db.delete(schema.subscribers)
      .where(eq(schema.subscribers.id, id))
      .run();
    return c.json({ ok: true });
  });

  app.post("/campaigns/:id/send", async (c) => {
    const id = Number(c.req.param("id"));
    try {
      await sendCampaign(db, config, id);
      return c.json({ ok: true });
    } catch (err: any) {
      return c.json({ error: err.message }, 400);
    }
  });

  return app;
}
```

**Step 2: Commit**

```bash
git add src/routes/api.ts
git commit -m "feat: add API routes (subscribers CRUD, campaign send)"
```

---

### Task 11: Admin UI routes

**Files:**
- Create: `src/routes/admin.tsx`

This is the largest task. The admin UI provides: dashboard, subscriber management, list management, campaign creation/editing/sending/previewing, and inbound message viewing with reply capability.

**Step 1: Create the admin routes file**

`src/routes/admin.tsx`:

```tsx
import { Hono } from "hono";
import { eq, desc, sql, and } from "drizzle-orm";
import { getCookie, setCookie, deleteCookie } from "hono/cookie";
import {
  S3Client,
  GetObjectCommand,
} from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";
import { SESv2Client, SendEmailCommand } from "@aws-sdk/client-sesv2";
import { marked } from "marked";
import type { Db } from "../db";
import { schema } from "../db";
import type { Config } from "../config";
import { adminAuth, createSession, destroySession } from "../auth";
import { sendCampaign } from "../services/sender";
import { renderNewsletter } from "../../emails/render";

function AdminLayout({ children }: { children: any }) {
  return (
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>lists admin</title>
        <style>{`
          * { margin: 0; padding: 0; box-sizing: border-box; }
          body { font-family: system-ui, sans-serif; max-width: 960px; margin: 0 auto; padding: 1rem; }
          nav { display: flex; gap: 1rem; margin-bottom: 1.5rem; padding-bottom: 0.75rem; border-bottom: 1px solid #ddd; }
          nav a { color: #0066cc; text-decoration: none; }
          h1, h2 { margin-bottom: 1rem; }
          table { width: 100%; border-collapse: collapse; margin-bottom: 1rem; }
          th, td { padding: 0.5rem; text-align: left; border-bottom: 1px solid #eee; }
          th { background: #f9f9f9; }
          form { display: flex; flex-direction: column; gap: 0.75rem; max-width: 600px; }
          input, select, textarea, button { padding: 0.5rem; font-size: 1rem; }
          textarea { font-family: monospace; }
          button { cursor: pointer; background: #000; color: #fff; border: none; border-radius: 4px; width: fit-content; }
          .btn-danger { background: #cc0000; }
          .btn-secondary { background: #666; }
          a { color: #0066cc; }
          .verdict-pass { color: green; }
          .verdict-fail { color: red; }
          .stat { display: inline-block; padding: 0.5rem 1rem; background: #f5f5f5; border-radius: 4px; margin-right: 0.5rem; }
          .flash { padding: 0.75rem; margin-bottom: 1rem; border-radius: 4px; }
          .flash-success { background: #d4edda; color: #155724; }
          .flash-error { background: #f8d7da; color: #721c24; }
        `}</style>
      </head>
      <body>
        <nav>
          <a href="/admin/">Dashboard</a>
          <a href="/admin/subscribers">Subscribers</a>
          <a href="/admin/lists">Lists</a>
          <a href="/admin/campaigns">Campaigns</a>
          <a href="/admin/inbound">Inbound</a>
          <form method="POST" action="/admin/logout" style="margin-left:auto;display:inline;">
            <button class="btn-secondary" type="submit">Logout</button>
          </form>
        </nav>
        {children}
      </body>
    </html>
  );
}

export function adminRoutes(db: Db, config: Config) {
  const app = new Hono();

  // Login (unprotected)
  app.get("/login", (c) =>
    c.html(
      <html lang="en">
        <body style="font-family:system-ui;max-width:300px;margin:4rem auto;">
          <h1>lists admin</h1>
          <form method="POST" style="display:flex;flex-direction:column;gap:0.5rem;">
            <input type="password" name="password" placeholder="Password" required autofocus />
            <button style="padding:0.5rem;background:#000;color:#fff;border:none;border-radius:4px;cursor:pointer;" type="submit">Log in</button>
          </form>
        </body>
      </html>,
    ),
  );

  app.post("/login", async (c) => {
    const body = await c.req.parseBody();
    if (body.password !== config.authPassword) {
      return c.redirect("/admin/login");
    }
    const token = createSession();
    setCookie(c, "session", token, {
      path: "/",
      httpOnly: true,
      sameSite: "Lax",
      maxAge: 86400,
    });
    return c.redirect("/admin/");
  });

  app.post("/logout", (c) => {
    const session = getCookie(c, "session");
    if (session) destroySession(session);
    deleteCookie(c, "session");
    return c.redirect("/admin/login");
  });

  // Everything below requires auth
  app.use("/*", adminAuth(config.authPassword));

  // Dashboard
  app.get("/", (c) => {
    const subscriberCount = db
      .select({ count: sql<number>`count(*)` })
      .from(schema.subscribers)
      .where(eq(schema.subscribers.status, "active"))
      .get()?.count ?? 0;

    const listCount = db
      .select({ count: sql<number>`count(*)` })
      .from(schema.lists)
      .get()?.count ?? 0;

    const campaignCount = db
      .select({ count: sql<number>`count(*)` })
      .from(schema.campaigns)
      .get()?.count ?? 0;

    const recentCampaigns = db
      .select()
      .from(schema.campaigns)
      .orderBy(desc(schema.campaigns.createdAt))
      .limit(5)
      .all();

    return c.html(
      <AdminLayout>
        <h1>Dashboard</h1>
        <div>
          <span class="stat">Subscribers: {subscriberCount}</span>
          <span class="stat">Lists: {listCount}</span>
          <span class="stat">Campaigns: {campaignCount}</span>
        </div>
        <h2 style="margin-top:1.5rem;">Recent campaigns</h2>
        <table>
          <thead><tr><th>Subject</th><th>Status</th><th>Date</th></tr></thead>
          <tbody>
            {recentCampaigns.map((c) => (
              <tr>
                <td><a href={`/admin/campaigns/${c.id}`}>{c.subject}</a></td>
                <td>{c.status}</td>
                <td>{c.sentAt ?? c.createdAt}</td>
              </tr>
            ))}
            {recentCampaigns.length === 0 && (
              <tr><td colspan="3">No campaigns yet.</td></tr>
            )}
          </tbody>
        </table>
      </AdminLayout>,
    );
  });

  // Subscribers
  app.get("/subscribers", (c) => {
    const subscribers = db
      .select()
      .from(schema.subscribers)
      .orderBy(desc(schema.subscribers.createdAt))
      .all();

    return c.html(
      <AdminLayout>
        <h1>Subscribers ({subscribers.length})</h1>
        <table>
          <thead><tr><th>Email</th><th>Name</th><th>Status</th><th>Confirmed</th><th>Created</th></tr></thead>
          <tbody>
            {subscribers.map((s) => (
              <tr>
                <td>{s.email}</td>
                <td>{s.name ?? "-"}</td>
                <td>{s.status}</td>
                <td>{s.confirmedAt ? "Yes" : "No"}</td>
                <td>{s.createdAt}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </AdminLayout>,
    );
  });

  // Lists
  app.get("/lists", (c) => {
    const allLists = db.select().from(schema.lists).all();
    return c.html(
      <AdminLayout>
        <h1>Lists</h1>
        <table>
          <thead><tr><th>Slug</th><th>Name</th><th>Description</th></tr></thead>
          <tbody>
            {allLists.map((l) => (
              <tr>
                <td>{l.slug}</td>
                <td>{l.name}</td>
                <td>{l.description}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <h2>Create list</h2>
        <form method="POST" action="/admin/lists/new">
          <input name="slug" placeholder="slug (e.g. plow)" required />
          <input name="name" placeholder="Display name" required />
          <input name="description" placeholder="Description (optional)" />
          <button type="submit">Create</button>
        </form>
      </AdminLayout>,
    );
  });

  app.post("/lists/new", async (c) => {
    const body = await c.req.parseBody();
    db.insert(schema.lists)
      .values({
        slug: body.slug as string,
        name: body.name as string,
        description: (body.description as string) || "",
      })
      .run();
    return c.redirect("/admin/lists");
  });

  // Campaigns
  app.get("/campaigns", (c) => {
    const allCampaigns = db
      .select()
      .from(schema.campaigns)
      .orderBy(desc(schema.campaigns.createdAt))
      .all();

    return c.html(
      <AdminLayout>
        <h1>Campaigns</h1>
        <a href="/admin/campaigns/new">New campaign</a>
        <table style="margin-top:1rem;">
          <thead><tr><th>Subject</th><th>List</th><th>Status</th><th>Date</th></tr></thead>
          <tbody>
            {allCampaigns.map((c) => (
              <tr>
                <td><a href={`/admin/campaigns/${c.id}`}>{c.subject}</a></td>
                <td>{c.listId}</td>
                <td>{c.status}</td>
                <td>{c.sentAt ?? c.createdAt}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </AdminLayout>,
    );
  });

  app.get("/campaigns/new", (c) => {
    const allLists = db.select().from(schema.lists).all();
    return c.html(
      <AdminLayout>
        <h1>New campaign</h1>
        <form method="POST">
          <label>List</label>
          <select name="listId" required>
            {allLists.map((l) => (
              <option value={String(l.id)}>{l.name}</option>
            ))}
          </select>
          <label>From address</label>
          <input name="fromAddress" placeholder={`plow@${config.fromDomain}`} required />
          <label>Subject</label>
          <input name="subject" required />
          <label>Body (Markdown)</label>
          <textarea name="bodyMarkdown" rows={15} required />
          <button type="submit">Create draft</button>
        </form>
      </AdminLayout>,
    );
  });

  app.post("/campaigns/new", async (c) => {
    const body = await c.req.parseBody();
    const result = db
      .insert(schema.campaigns)
      .values({
        listId: Number(body.listId),
        fromAddress: body.fromAddress as string,
        subject: body.subject as string,
        bodyMarkdown: body.bodyMarkdown as string,
      })
      .returning()
      .get();

    return c.redirect(`/admin/campaigns/${result.id}`);
  });

  app.get("/campaigns/:id", (c) => {
    const id = Number(c.req.param("id"));
    const campaign = db
      .select()
      .from(schema.campaigns)
      .where(eq(schema.campaigns.id, id))
      .get();

    if (!campaign) return c.text("Not found", 404);

    const sends = db
      .select({ count: sql<number>`count(*)` })
      .from(schema.campaignSends)
      .where(eq(schema.campaignSends.campaignId, id))
      .get();

    return c.html(
      <AdminLayout>
        <h1>{campaign.subject}</h1>
        <p>Status: {campaign.status} | From: {campaign.fromAddress} | Sends: {sends?.count ?? 0}</p>
        <h2>Preview</h2>
        <div style="border:1px solid #ddd;padding:1rem;margin-bottom:1rem;" dangerouslySetInnerHTML={{ __html: marked(campaign.bodyMarkdown) as string }} />
        {campaign.status === "draft" && (
          <form method="POST" action={`/admin/campaigns/${id}/send`}>
            <button class="btn-danger" type="submit"
              onclick="return confirm('Send this campaign to all confirmed subscribers?')">
              Send campaign
            </button>
          </form>
        )}
      </AdminLayout>,
    );
  });

  app.post("/campaigns/:id/send", async (c) => {
    const id = Number(c.req.param("id"));
    try {
      await sendCampaign(db, config, id);
    } catch (err: any) {
      return c.text(err.message, 400);
    }
    return c.redirect(`/admin/campaigns/${id}`);
  });

  // Inbound messages
  app.get("/inbound", (c) => {
    const messages = db
      .select()
      .from(schema.inboundMessages)
      .orderBy(desc(schema.inboundMessages.createdAt))
      .limit(100)
      .all();

    const verdictClass = (v: string | null) =>
      v === "PASS" ? "verdict-pass" : v ? "verdict-fail" : "";

    return c.html(
      <AdminLayout>
        <h1>Inbound messages ({messages.length})</h1>
        <table>
          <thead>
            <tr><th>Date</th><th>From</th><th>Subject</th><th>SPF</th><th>DKIM</th><th>DMARC</th></tr>
          </thead>
          <tbody>
            {messages.map((m) => (
              <tr>
                <td>{m.timestamp}</td>
                <td>{m.source}</td>
                <td><a href={`/admin/inbound/${m.id}`}>{m.subject}</a></td>
                <td class={verdictClass(m.spfVerdict)}>{m.spfVerdict ?? "-"}</td>
                <td class={verdictClass(m.dkimVerdict)}>{m.dkimVerdict ?? "-"}</td>
                <td class={verdictClass(m.dmarcVerdict)}>{m.dmarcVerdict ?? "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </AdminLayout>,
    );
  });

  app.get("/inbound/:id", (c) => {
    const id = Number(c.req.param("id"));
    const msg = db
      .select()
      .from(schema.inboundMessages)
      .where(eq(schema.inboundMessages.id, id))
      .get();

    if (!msg) return c.text("Not found", 404);

    const msgReplies = db
      .select()
      .from(schema.replies)
      .where(eq(schema.replies.inboundMessageId, id))
      .all();

    // Derive from address
    let toAddrs: string[] = [];
    try { toAddrs = JSON.parse(msg.toAddrs); } catch {}
    const localPart = toAddrs[0]?.split("@")[0] ?? "noreply";
    const defaultFrom = `${localPart}@${config.fromDomain}`;

    return c.html(
      <AdminLayout>
        <h1>Inbound #{msg.id}</h1>
        <table>
          <tr><th>From</th><td>{msg.source}</td></tr>
          <tr><th>To</th><td>{msg.toAddrs}</td></tr>
          <tr><th>Subject</th><td>{msg.subject}</td></tr>
          <tr><th>Date</th><td>{msg.timestamp}</td></tr>
          {msg.s3Key && (
            <tr><th>Raw</th><td><a href={`/admin/inbound/${msg.id}/raw`}>Download .eml</a></td></tr>
          )}
        </table>

        {msgReplies.length > 0 && (
          <>
            <h2 style="margin-top:1rem;">Replies sent</h2>
            <table>
              <thead><tr><th>Date</th><th>From</th><th>Subject</th></tr></thead>
              <tbody>
                {msgReplies.map((r) => (
                  <tr><td>{r.sentAt}</td><td>{r.fromAddr}</td><td>{r.subject}</td></tr>
                ))}
              </tbody>
            </table>
          </>
        )}

        <h2 style="margin-top:1rem;">Send reply</h2>
        <form method="POST" action={`/admin/inbound/${msg.id}/reply`}>
          <label>From</label>
          <input name="from" value={defaultFrom} required style="width:100%;" />
          <label>Reply</label>
          <textarea name="body" rows={8} required style="width:100%;" />
          <button type="submit">Send reply</button>
        </form>
      </AdminLayout>,
    );
  });

  app.get("/inbound/:id/raw", async (c) => {
    const id = Number(c.req.param("id"));
    const msg = db
      .select()
      .from(schema.inboundMessages)
      .where(eq(schema.inboundMessages.id, id))
      .get();

    if (!msg?.s3Key) return c.text("Not found", 404);

    const s3 = new S3Client({ region: config.awsRegion });
    const url = await getSignedUrl(
      s3,
      new GetObjectCommand({ Bucket: config.s3Bucket, Key: msg.s3Key }),
      { expiresIn: 900 },
    );
    return c.redirect(url);
  });

  app.post("/inbound/:id/reply", async (c) => {
    const id = Number(c.req.param("id"));
    const msg = db
      .select()
      .from(schema.inboundMessages)
      .where(eq(schema.inboundMessages.id, id))
      .get();

    if (!msg) return c.text("Not found", 404);

    const body = await c.req.parseBody();
    const fromAddr = body.from as string;
    const replyBody = body.body as string;

    let subject = msg.subject;
    if (!subject.toLowerCase().startsWith("re:")) subject = `Re: ${subject}`;

    // Build raw email with threading headers
    // For now, skip S3 header parsing -- just send without In-Reply-To
    // (Part 2 enhancement: fetch .eml headers for threading)
    const rawLines = [
      `From: ${fromAddr}`,
      `To: ${msg.source}`,
      `Subject: ${subject}`,
      `MIME-Version: 1.0`,
      `Content-Type: text/plain; charset=UTF-8`,
      ``,
      replyBody,
    ];

    const ses = new SESv2Client({ region: config.awsRegion });
    const result = await ses.send(
      new SendEmailCommand({
        Content: {
          Raw: { Data: new TextEncoder().encode(rawLines.join("\r\n")) },
        },
      }),
    );

    db.insert(schema.replies)
      .values({
        inboundMessageId: id,
        fromAddr,
        toAddr: msg.source,
        subject,
        body: replyBody,
        sesMessageId: result.MessageId,
      })
      .run();

    return c.redirect(`/admin/inbound/${id}`);
  });

  return app;
}
```

**Step 2: Verify it compiles**

Run: `bun build src/index.ts --target=bun --outdir=dist`
Expected: No errors.

**Step 3: Commit**

```bash
git add src/routes/admin.tsx
git commit -m "feat: add admin UI routes (dashboard, subscribers, lists, campaigns, inbound)"
```

---

### Task 12: Wire everything together in index.ts

**Files:**
- Modify: `src/index.ts`

**Step 1: Update the entry point**

```typescript
import { Hono } from "hono";
import { loadConfig } from "./config";
import { createDb } from "./db";
import { publicRoutes } from "./routes/public";
import { apiRoutes } from "./routes/api";
import { adminRoutes } from "./routes/admin";
import { startPoller } from "./services/poller";

const config = loadConfig();
const db = createDb(config.dbPath);

const app = new Hono();

// Public routes (subscribe, confirm, unsubscribe, preferences)
app.route("/", publicRoutes(db, config));

// API routes (bearer token auth)
app.route("/api", apiRoutes(db, config));

// Admin routes (session auth)
app.route("/admin", adminRoutes(db, config));

// Start SQS poller in the background
startPoller(db, config).catch((err) => {
  console.error("Poller crashed:", err);
  process.exit(1);
});

console.log("lists running on :8080");

export default {
  port: 8080,
  fetch: app.fetch,
};
```

**Step 2: Verify it compiles and runs**

Run: `SQS_QUEUE_URL=fake S3_BUCKET=fake AUTH_PASSWORD=test API_TOKEN=test BASE_URL=http://localhost:8080 DB_PATH=./test.db bun run src/index.ts`
Expected: Starts on :8080, SQS poller logs an error (expected), admin login page at `/admin/login`, subscribe page at `/subscribe`.

Run: `rm test.db`

**Step 3: Commit**

```bash
git add src/index.ts
git commit -m "feat: wire up all routes and SQS poller in entry point"
```

---

### Task 13: Build Docker image and test locally

**Step 1: Build image**

Run: `docker build -t lists:test .`
Expected: Build succeeds.

**Step 2: Run it**

Run:
```bash
docker run --rm -p 8080:8080 \
  -e SQS_QUEUE_URL=fake -e S3_BUCKET=fake \
  -e AUTH_PASSWORD=test -e API_TOKEN=test \
  -e BASE_URL=http://localhost:8080 \
  lists:test
```

Expected: Container starts. `http://localhost:8080/subscribe` shows the subscribe form (with no lists). `http://localhost:8080/admin/login` shows login.

**Step 3: Commit final touches**

```bash
git add -A
git commit -m "chore: verify docker build and local test"
```

---

### Task 14: Push and verify CI

**Step 1: Push to GitHub**

Run: `git push origin main`

**Step 2: Verify GitHub Actions builds and pushes image**

Run: `gh run watch`
Expected: Build succeeds, image pushed to `ghcr.io/jackharrhy/lists:main`.

**Step 3: Verify image pull**

Run: `docker pull ghcr.io/jackharrhy/lists:main`
Expected: Succeeds.

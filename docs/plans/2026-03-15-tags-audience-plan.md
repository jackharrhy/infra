# Tags and Audience Targeting Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add subscriber tags for internal segmentation and a multi-mode campaign audience selector (list, all, tag, specific people).

**Architecture:** New `tags` and `subscriber_tags` tables. New `audience` JSON column on campaigns. Sender resolves audience to subscribers at send time. Admin UI gets tags CRUD pages, subscriber tag management, and a campaign audience picker with JS-driven mode switching.

**Tech Stack:** Drizzle ORM (SQLite), Hono JSX, Tailwind CSS, existing test infra.

**Design doc:** `docs/plans/2026-03-15-tags-audience-design.md`

---

### Task 1: Schema — tags, subscriber_tags, campaign audience

**Files:**
- Modify: `src/db/schema.ts`
- Migration: `drizzle/`

**Step 1:** Add tags table:
```typescript
export const tags = sqliteTable("tags", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  name: text("name").unique().notNull(),
  createdAt: text("created_at")
    .notNull()
    .$defaultFn(() => new Date().toISOString()),
});
```

**Step 2:** Add subscriber_tags junction table:
```typescript
export const subscriberTags = sqliteTable("subscriber_tags", {
  subscriberId: integer("subscriber_id")
    .notNull()
    .references(() => subscribers.id),
  tagId: integer("tag_id")
    .notNull()
    .references(() => tags.id),
});
```

**Step 3:** Add `audience` column to campaigns:
```typescript
audience: text("audience"), // JSON: { type: "all" } | { type: "tag", tagId: N } | { type: "subscribers", subscriberIds: [...] }
```

**Step 4:** Generate migration: `bunx drizzle-kit generate --name=add-tags-and-audience`

**Step 5:** Run `bun test`, commit.

---

### Task 2: Tags CRUD admin pages

**Files:**
- Modify: `src/routes/admin.tsx`

**Step 1:** Add "Tags" to admin nav (visible to all roles).

**Step 2:** `GET /admin/tags` — list all tags with subscriber count per tag. "New Tag" button.

**Step 3:** `GET /admin/tags/new` — form with tag name field.

**Step 4:** `POST /admin/tags/new` — insert tag, redirect to /admin/tags. Log event.

**Step 5:** `GET /admin/tags/:id` — tag detail: shows name, created date, all subscribers with this tag in a table. Delete button.

**Step 6:** `POST /admin/tags/:id/delete` — delete subscriber_tags entries, delete tag, redirect to /admin/tags. Log event.

**Step 7:** Route ordering: `/admin/tags/new` before `/admin/tags/:id`.

**Step 8:** Run `bun test`, commit.

---

### Task 3: Subscriber tag management

**Files:**
- Modify: `src/routes/admin.tsx` (subscriber detail page)

**Step 1:** On subscriber detail page (`GET /admin/subscribers/:id`), add a "Tags" section:
- Show current tags as removable badges/chips
- Each badge has a small form that POSTs to `/admin/subscribers/:id/tags/:tagId/remove`
- Below: a dropdown of all tags (excluding already-applied ones) with an "Add" button that POSTs to `/admin/subscribers/:id/tags/add`

**Step 2:** `POST /admin/subscribers/:id/tags/add` — parse tagId from form body, insert subscriber_tags, redirect back.

**Step 3:** `POST /admin/subscribers/:id/tags/:tagId/remove` — delete from subscriber_tags, redirect back.

**Step 4:** Run `bun test`, commit.

---

### Task 4: CSV import — tag support

**Files:**
- Modify: `src/routes/admin.tsx` (import routes)

**Step 1:** On the column mapping page (`POST /admin/import/upload`), add:
- A text input: "Apply tag to all imported subscribers" (optional, type a tag name)
- This creates the tag if it doesn't exist and applies it to all imported subscribers

**Step 2:** On the processing route (`POST /admin/import/process`):
- If a tag name is provided: find or create the tag
- After each subscriber is created/found: insert into subscriber_tags (with onConflictDoNothing)

**Step 3:** Run `bun test`, commit.

---

### Task 5: Campaign audience selector UI

**Files:**
- Modify: `src/routes/admin.tsx` (campaign new page)

**Step 1:** Replace the current list dropdown + "All subscribers" with a mode selector:

```html
<select id="audienceMode">
  <option value="list">A list</option>
  <option value="all">All subscribers</option>
  <option value="tag">A tag</option>
  <option value="specific">Specific people</option>
</select>
```

**Step 2:** Below the mode selector, show/hide sub-selectors via JS:
- `list` mode: existing list dropdown (id="listId")
- `all` mode: nothing extra
- `tag` mode: tag dropdown (id="tagId")
- `specific` mode: searchable subscriber picker

**Step 3:** The subscriber picker for "specific" mode:
- A text input that filters subscribers (client-side or server endpoint)
- For simplicity: render all subscribers as a JSON array in a script tag, filter client-side
- Matching subscribers shown as clickable items
- Clicking adds to a "selected" list shown as removable badges
- Hidden input stores selected subscriber IDs as comma-separated: `<input type="hidden" name="subscriberIds" />`

**Step 4:** JS for mode switching:
```javascript
document.getElementById('audienceMode').addEventListener('change', function() {
  document.querySelectorAll('[data-audience]').forEach(el => el.classList.add('hidden'));
  var target = document.querySelector('[data-audience="' + this.value + '"]');
  if (target) target.classList.remove('hidden');
});
```

**Step 5:** From address auto-fill: when mode is "list", auto-fill from list's fromAddress (existing). Other modes: clear auto-fill.

**Step 6:** Run `bun test`, commit.

---

### Task 6: Campaign creation POST — audience handling

**Files:**
- Modify: `src/routes/admin.tsx` (campaign new POST handler)

**Step 1:** Parse the audience mode from form body:
- `audienceMode === "list"`: set listId, audience null (existing behavior)
- `audienceMode === "all"`: set listId null, audience `{ "type": "all" }`
- `audienceMode === "tag"`: set listId null, audience `{ "type": "tag", "tagId": N }`
- `audienceMode === "specific"`: set listId null, audience `{ "type": "subscribers", "subscriberIds": [N, N, N] }` (parse from comma-separated hidden input)

**Step 2:** Insert campaign with listId and audience.

**Step 3:** Run `bun test`, commit.

---

### Task 7: Sender — resolve audience types

**Files:**
- Modify: `src/services/sender.ts`

**Step 1:** In `sendCampaign`, after the existing listId check, add audience resolution:

```typescript
if (campaign.listId) {
  // existing: get subscribers for list
} else if (campaign.audience) {
  const aud = JSON.parse(campaign.audience);
  if (aud.type === "all") {
    subscribers = getAllActiveConfirmedSubscribers(db);
  } else if (aud.type === "tag") {
    subscribers = getSubscribersByTag(db, aud.tagId);
  } else if (aud.type === "subscribers") {
    subscribers = getSubscribersByIds(db, aud.subscriberIds);
  }
}
```

**Step 2:** Add helper functions:
- `getSubscribersByTag(db, tagId)`: join subscribers with subscriber_tags where tagId matches, filter active + confirmed
- `getSubscribersByIds(db, ids)`: select subscribers by IDs, filter active + confirmed

**Step 3:** Run `bun test`, commit.

---

### Task 8: Campaign display — audience description

**Files:**
- Modify: `src/routes/admin.tsx`

**Step 1:** Campaign list page: show audience description instead of just list name:
- listId set: "List: {name}"
- audience all: "All subscribers"
- audience tag: "Tag: {name}" (look up tag name)
- audience subscribers: "N specific subscribers"

**Step 2:** Campaign detail page: same audience description in the header area.

**Step 3:** Run `bun test`, commit.

---

### Task 9: Tests

**Files:**
- Modify: `tests/e2e.test.ts`
- Modify: `tests/subscriber.test.ts`

**Step 1:** Test tag-targeted campaign send:
- Create tag, apply to 2 subscribers, create campaign with audience `{ type: "tag", tagId }`, mock SES, send
- Assert SES called twice, campaign sent

**Step 2:** Test specific-subscribers campaign send:
- Create campaign with audience `{ type: "subscribers", subscriberIds: [1, 2] }`, mock SES, send
- Assert SES called twice

**Step 3:** Test subscriber tag management:
- Create subscriber + tag, add tag to subscriber, verify subscriber_tags entry
- Remove tag, verify entry gone

**Step 4:** Run `bun test`, commit.

---

### Task 10: Final verification

**Step 1:** Run `bun test`

**Step 2:** Docker build: `docker build -t lists:test .`

**Step 3:** Push: `git push origin main`

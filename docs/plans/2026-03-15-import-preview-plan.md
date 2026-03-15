# CSV Import, Segment Sends, and Email Previews Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add CSV subscriber import with column mapping, campaigns that target all subscribers, and a live email preview system with per-subscriber personalization.

**Architecture:** CSV import is a new admin page with file upload, server-side parsing, and column mapping UI. Segment sends extend campaigns with nullable listId. Email previews add render endpoints that return raw HTML for iframe embedding, using the same react-email templates the sender uses.

**Tech Stack:** Bun (built-in CSV parsing or manual split), Hono (multipart file upload), Drizzle ORM, react-email render, existing test infra.

**Design doc:** `docs/plans/2026-03-15-import-preview-design.md`

---

### Task 1: Schema — make campaigns.listId nullable

**Files:**
- Modify: `src/db/schema.ts`
- Migration: `drizzle/`

**Step 1:** Change `campaigns.listId` from `.notNull()` to optional (remove `.notNull()`). The FK reference stays.

**Step 2:** Generate migration: `bunx drizzle-kit generate --name=nullable-campaign-listid`

**Step 3:** Run `bun test` to verify nothing broke. Some tests may need updating if they assert on listId being required.

**Step 4:** Commit: `git commit -m "schema: make campaigns.listId nullable for segment sends"`

---

### Task 2: Sender — support campaigns without a list

**Files:**
- Modify: `src/services/sender.ts`

**Step 1:** In `sendCampaign`, when `campaign.listId` is null:
- Query all active confirmed subscribers (deduplicated by email) via: select distinct subscribers where status="active" and has at least one confirmed subscriberList
- Use `config.fromDomain` for Reply-To instead of `list.slug@reply.{domain}`
- Use the campaign's `fromAddress` directly (no list display name wrapper -- or use "Newsletter" as fallback)
- The `renderNewsletter` call uses a generic list name (e.g. the from domain)

**Step 2:** Update the "already sent" skip logic to work without a list.

**Step 3:** Run `bun test` -- update e2e tests if needed.

**Step 4:** Commit: `git commit -m "sender: support campaigns targeting all subscribers (null listId)"`

---

### Task 3: Campaign UI — "All subscribers" option

**Files:**
- Modify: `src/routes/admin.tsx`

**Step 1:** Campaign new page: add `<option value="all">All subscribers</option>` as the first option in the list dropdown.

**Step 2:** Campaign new POST handler: if `listId === "all"`, set listId to null in the insert.

**Step 3:** Campaign detail page: show "All subscribers" when listId is null. The send button should still work.

**Step 4:** Campaign list page: show "All" in the list column when listId is null.

**Step 5:** The "From Address" auto-fill JS: when "All subscribers" is selected, don't try to auto-fill (no list to get fromAddress from).

**Step 6:** Commit: `git commit -m "campaigns: add 'All subscribers' targeting option"`

---

### Task 4: Email preview endpoints

**Files:**
- Modify: `src/routes/admin.tsx`
- Use: `emails/render.ts` (renderNewsletter)

**Step 1:** Add `GET /admin/campaigns/:id/preview`:
- Get campaign from DB
- Get list (if listId set)
- If `subscriberId` query param: look up subscriber, build real unsubscribe/preferences URLs
- If no subscriberId: use placeholder URLs (`#unsubscribe`, `#preferences`)
- Render markdown to HTML via `marked`
- Call `renderNewsletter` with the content, subject, list name, URLs
- Return raw HTML (no AdminLayout wrapper) with `Content-Type: text/html`

**Step 2:** Add `POST /admin/campaigns/preview`:
- Parse JSON body: `{ bodyMarkdown, subject, listName }`
- Render markdown, call renderNewsletter with placeholders
- Return raw HTML

**Step 3:** Commit: `git commit -m "preview endpoints: render campaign as email HTML"`

---

### Task 5: Campaign detail — preview tab with subscriber picker

**Files:**
- Modify: `src/routes/admin.tsx`

**Step 1:** On campaign detail page, add a "Preview" section below the markdown render:
- An iframe that loads `/admin/campaigns/:id/preview`
- A subscriber dropdown (populated from the campaign's list subscribers, or all subscribers if listId is null)
- Changing the dropdown updates the iframe src with `?subscriberId=N`
- Style the iframe: `width: 100%; border: 1px solid #e5e5e5; border-radius: 8px; min-height: 600px;`

**Step 2:** Add JS to update iframe on subscriber select change.

**Step 3:** Commit: `git commit -m "campaign detail: email preview iframe with subscriber picker"`

---

### Task 6: Campaign editor — live split preview

**Files:**
- Modify: `src/routes/admin.tsx`

**Step 1:** On the new campaign page (`/admin/campaigns/new`), change layout to side-by-side:
- Left side: the existing form
- Right side: iframe showing preview
- Use CSS grid or flex: `grid-cols-2` with a gap

**Step 2:** Add JS that:
- On textarea blur (or 500ms debounce after keyup), POSTs the markdown body to `/admin/campaigns/preview`
- Takes the returned HTML and sets it as the iframe srcdoc
- Also sends subject and list name from the form

**Step 3:** Handle the initial state: iframe starts with a placeholder message "Start writing to see a preview"

**Step 4:** Commit: `git commit -m "campaign editor: live split preview while writing"`

---

### Task 7: CSV import — upload and parse

**Files:**
- Modify: `src/routes/admin.tsx`

**Step 1:** Add "Import" to admin nav (visible to owner/admin).

**Step 2:** Add `GET /admin/import` page:
- File upload form (`enctype="multipart/form-data"`)
- Submit uploads CSV to `POST /admin/import/parse`

**Step 3:** Add `POST /admin/import/parse`:
- Read file from multipart body via `c.req.parseBody()`
- Parse CSV: split by newlines, split by comma (handle quoted fields)
- Store parsed data in a hidden form field (JSON) for the next step
- Render column mapping UI:
  - Table showing first 5 rows
  - Dropdown above each column: "email", "name", "ignore"
  - Auto-detect: if column header contains "email" or "mail", pre-select "email"; if "name", pre-select "name"
  - List checkboxes: which lists to subscribe to
  - Pre-confirm checkbox
  - Hidden field with full parsed CSV data (JSON)
  - Submit button: "Import"

**Step 4:** Commit: `git commit -m "csv import: upload, parse, column mapping UI"`

---

### Task 8: CSV import — process and insert

**Files:**
- Modify: `src/routes/admin.tsx`

**Step 1:** Add `POST /admin/import/process`:
- Parse form: column mappings (emailCol, nameCol), list slugs, pre-confirm flag, CSV data (JSON)
- For each row: extract email and name based on mappings
- Call `createSubscriber(db, email, name, listSlugs)`
- If pre-confirm: call `confirmSubscriber(db, subscriber.unsubscribeToken)`
- Track counts: imported, skipped (duplicate email that was already subscribed), errors (invalid email, etc.)
- Log event: `admin.import_completed` with counts

**Step 2:** Render result page:
- "Import complete: X imported, Y skipped, Z errors"
- Link back to subscribers page

**Step 3:** Commit: `git commit -m "csv import: process rows, bulk create subscribers"`

---

### Task 9: Tests

**Files:**
- Modify: `tests/e2e.test.ts`

**Step 1:** Test campaign with null listId:
- Create a campaign with listId null
- Mock SES, call sendCampaign
- Verify all confirmed subscribers across all lists receive the email (deduplicated)

**Step 2:** Test preview endpoint:
- Create a campaign, GET `/admin/campaigns/:id/preview`
- Verify response is HTML containing the campaign subject and content
- With subscriberId: verify response contains real unsubscribe URL

**Step 3:** Run full suite: `bun test`

**Step 4:** Commit: `git commit -m "tests: segment sends, preview endpoints"`

---

### Task 10: Final verification

**Step 1:** Run full test suite: `bun test`

**Step 2:** Docker build: `docker build -t lists:test .`

**Step 3:** Push: `git push origin main`

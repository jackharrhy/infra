# CSV Import, Segment Sends, and Email Previews Design

## Summary

Three related features: bulk CSV import with column mapping, campaigns that can target all subscribers (segment sends), and a full email preview system with live editing and per-subscriber personalization.

## 1. CSV Import

### UI Flow

New admin page at `/admin/import`.

1. **Upload**: File input accepts `.csv`. Server parses with a CSV parser.
2. **Preview + Map**: Shows first 5 rows in a table. Above each column, a dropdown: "email" (required), "name", or "ignore". Server detects likely mappings as defaults (columns named "email", "name", etc.).
3. **Options**: 
   - Target list(s): checkboxes
   - Pre-confirm toggle: "Pre-confirm subscribers (skip double opt-in)" checkbox
4. **Submit**: Bulk import. Uses existing `createSubscriber` per row. If pre-confirm is checked, calls `confirmSubscriber` on each.
5. **Result**: "X imported, Y skipped (duplicate), Z errors" summary.

### No schema changes

Uses existing subscriber and subscriberLists tables. Import is just a batch create.

## 2. Segment Sends (All Subscribers)

### Approach

Add an "All subscribers" option to the campaign list selector. When selected, the campaign sends to all active confirmed subscribers across all lists, deduplicating by email.

### Schema change

Make `campaigns.listId` nullable. A campaign with `listId = null` targets all subscribers.

### Sender changes

In `sendCampaign`:
- If `campaign.listId` is set: existing behavior (get confirmed subscribers for that list)
- If `campaign.listId` is null: query all active confirmed subscribers (deduplicated), use config.fromDomain for Reply-To since there's no specific list

### UI changes

Campaign creation form: list dropdown gets an "All subscribers" option with value "all". The POST handler sets `listId = null` when "all" is selected.

Campaign detail page: shows "All subscribers" instead of a list name when listId is null.

## 3. Email Previews

### Preview endpoint

`GET /admin/campaigns/:id/preview` -- renders the full react-email newsletter template to HTML and returns it.

Query params:
- `subscriberId=N` -- optional. If provided, renders with that subscriber's real unsubscribe/preferences URLs. If not, uses placeholder URLs.

Returns raw HTML (not wrapped in admin layout) suitable for iframe embedding.

### Preview for unsaved campaigns

`POST /admin/campaigns/preview` -- accepts JSON body with `{ bodyMarkdown, subject, listId }`, renders a generic preview. Returns raw HTML.

### Campaign editor (new campaign page)

Split layout:
- Left: the existing form (list, from, subject, markdown body)
- Right: iframe showing the preview
- The iframe src hits the POST preview endpoint
- Updates on textarea blur or a debounce after typing stops

### Campaign detail page

- "Preview" tab/button that shows the rendered email in an iframe
- Subscriber dropdown: select a subscriber from the campaign's list to see their personalized version
- Changing the subscriber updates the iframe src with `?subscriberId=N`

### Implementation notes

The preview renders using the same `renderNewsletter` function the sender uses, ensuring what you see is what gets sent. The only difference is the unsubscribe/preferences URLs -- preview uses real URLs for specific subscribers or placeholder text for generic preview.

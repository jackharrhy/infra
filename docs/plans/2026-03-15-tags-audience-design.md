# Tags and Audience Targeting Design

## Summary

Add a tagging system for internal subscriber segmentation and replace the campaign list dropdown with a multi-mode audience selector supporting lists, tags, all subscribers, and specific people.

## Tags

Internal admin labels for organizing subscribers. Subscribers never see tags -- they only see lists. Tags are for segmentation and one-off sends.

### Schema

```
tags:
  id        INTEGER PK autoincrement
  name      TEXT unique not null
  createdAt TEXT not null

subscriber_tags:
  subscriberId  INTEGER FK -> subscribers.id, not null
  tagId         INTEGER FK -> tags.id, not null
  (composite unique on subscriberId + tagId)
```

### Where tags appear

- **Subscriber detail page**: shows tags, add/remove tags
- **CSV import**: option to apply a fixed tag to all imported subscribers (e.g. "imported-2026-03"), or map a CSV column to tag
- **Tags management page** (`/admin/tags`): list all tags with subscriber counts, create/delete
- **Tag detail page** (`/admin/tags/:id`): all subscribers with that tag

### Tag CRUD

- Create: from tags page or inline when tagging a subscriber (type a new name)
- Delete: from tags page. Removes all subscriber_tags entries for that tag.
- No edit (tags are simple labels, just delete and recreate if needed)

## Campaign Audience Selector

### Schema change

Add `audience` column to campaigns (text, JSON, nullable).

When `listId` is set: `audience` is null (existing list-based targeting).
When `listId` is null: `audience` stores targeting criteria.

Audience JSON shapes:
- `{ "type": "all" }` -- all active confirmed subscribers
- `{ "type": "tag", "tagId": 5 }` -- subscribers with that tag who are active+confirmed
- `{ "type": "subscribers", "subscriberIds": [1, 3, 7] }` -- specific subscriber IDs, active+confirmed

### UI

Campaign creation form audience section:

```
Audience: [ A list ▾ ]

  → "A list":          [ list dropdown ]
  → "All subscribers": (no sub-selector)
  → "A tag":           [ tag dropdown ]
  → "Specific people": [ searchable multi-select ]
```

JS toggles which sub-selector is visible based on the audience mode dropdown.

For "Specific people": a text input that filters subscribers by email/name as you type, with clickable results that add to a selected list below. Selected people shown as removable chips/badges.

### Sender changes

In `sendCampaign`, resolve audience to subscriber list:

- `listId` set: existing behavior (get confirmed subscribers for list)
- `audience.type === "all"`: all active confirmed subscribers (existing null-listId behavior)
- `audience.type === "tag"`: join subscribers with subscriber_tags where tagId matches, filter active+confirmed
- `audience.type === "subscribers"`: select subscribers by IDs, filter active+confirmed

### Unsubscribe behavior

- List campaigns: per-list unsubscribe URL (existing)
- Tag/All/Specific campaigns: legacy unsubscribe-all URL (no specific list context)

### Campaign display

Campaign detail and list pages show audience description:
- "List: DO. IT 3"
- "All subscribers"
- "Tag: imported-2026-03"
- "3 specific subscribers"

# User Accounts Design

## Summary

Replace the single shared password with a multi-user system. Users have email/password credentials, one of three roles, and list-scoped access for non-admin users.

## Current state

- Single `AUTH_PASSWORD` env var shared by all admins
- In-memory session map (token -> expiry)
- No concept of who performed an action
- Activity feed logs events without attribution

## Roles

| Role | Scope | Capabilities |
|------|-------|-------------|
| owner | Global | Everything. Manage users, create/delete lists, assign members to lists, system config. |
| admin | Global | Everything except managing owners. Can see all lists. |
| member | Per-list | Full control over assigned lists: view/manage subscribers, create/send campaigns, view/reply to inbound, edit list settings. Cannot see other lists, manage users, or create/delete lists. |

## Schema changes

New tables:

```
users:
  id          INTEGER PK autoincrement
  email       TEXT unique not null
  name        TEXT
  passwordHash TEXT not null
  role        TEXT not null (owner | admin | member)
  createdAt   TEXT not null

user_lists:
  userId      INTEGER FK -> users.id, not null
  listId      INTEGER FK -> lists.id, not null
  (composite unique on userId + listId)
```

Modified tables:

```
events:
  + userId    INTEGER FK -> users.id (nullable, for backwards compat)
```

## Authentication

- Email + password login (replaces single password)
- Passwords hashed with Bun's built-in `Bun.password.hash()` (argon2id)
- Sessions store userId instead of just "valid"
- Session map: `token -> { userId, expiry }`
- Cookie-based, same as current

## First user bootstrap

On startup, if the `users` table is empty and `OWNER_EMAIL` + `OWNER_PASSWORD` env vars are set, auto-create the owner account. This replaces `AUTH_PASSWORD`.

After bootstrap, `OWNER_PASSWORD` can be removed from the env (the hash is in the DB). `AUTH_PASSWORD` is no longer used.

## Authorization

### Middleware

- `adminAuth` middleware reads session cookie, looks up user, attaches to context
- New `requireRole(roles[])` middleware checks user role
- New `requireListAccess(listId)` middleware checks user is owner/admin OR is a member with access to that list

### Route protection

| Route group | Access |
|-------------|--------|
| `/admin/users/*` | owner, admin |
| `/admin/lists/new`, `/admin/lists/:id/delete` | owner, admin |
| `/admin/lists/:id/*` | owner, admin, or member with list access |
| `/admin/campaigns/*` | owner, admin, or member with access to campaign's list |
| `/admin/inbound/*` | owner, admin, or member with access to linked campaign's list |
| `/admin/subscribers/*` | owner, admin see all; members see only subscribers on their lists |
| `/admin/activity` | owner, admin see all; members see events for their lists |
| `/admin/` (dashboard) | all users, stats scoped to accessible lists |
| `/api/*` | bearer token (unchanged) |

### Filtered views for members

Members see the same UI but filtered:
- Lists page: only their lists
- Campaigns: only campaigns on their lists
- Subscribers: only subscribers on their lists
- Inbound: only messages linked to their lists' campaigns
- Activity: only events for their lists
- Dashboard stats: scoped to their lists

## Admin UI additions

### Users page (`/admin/users`)

Owner/admin only. Shows all users with email, name, role, created date.

### Invite user (`/admin/users/new`)

Form: email, name, temporary password, role (admin or member), list assignments (checkboxes, shown if member).

### User detail (`/admin/users/:id`)

Edit name, role, list assignments. Reset password. Delete user.

### Login page

Changes from single password field to email + password fields.

## Activity feed changes

Events gain a `userId` field. The feed displays "Jack created subscriber..." instead of "admin created subscriber...". All action points that currently call `logEvent` pass the current user's ID.

## Migration path

1. Add `users` and `user_lists` tables
2. Add `userId` column to `events` (nullable)
3. Update session system (in-memory map stores userId)
4. Update login page (email + password)
5. Update `adminAuth` middleware to load user from session
6. Add role/list-access middleware
7. Filter all admin queries by user access
8. Add users management pages
9. Bootstrap owner on first start
10. Remove `AUTH_PASSWORD` from config

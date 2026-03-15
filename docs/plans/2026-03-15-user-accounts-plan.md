# User Accounts Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace single shared password with multi-user system supporting owner/admin/member roles with per-list access control.

**Architecture:** Add `users` and `user_lists` tables to SQLite. Sessions store userId. Middleware loads user and checks role/list access. Admin UI filters queries by user permissions. Owner account bootstrapped from env vars on first start.

**Tech Stack:** Bun (Bun.password for argon2id hashing), Drizzle ORM, Hono middleware, existing test infra with bun:test.

**Design doc:** `docs/plans/2026-03-15-user-accounts-design.md`

---

### Task 1: Schema — users and user_lists tables

**Files:**
- Modify: `src/db/schema.ts`
- Migration: `drizzle/`

**Step 1: Add users table to schema**

```typescript
export const users = sqliteTable("users", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  email: text("email").unique().notNull(),
  name: text("name"),
  passwordHash: text("password_hash").notNull(),
  role: text("role", { enum: ["owner", "admin", "member"] }).notNull().default("member"),
  createdAt: text("created_at")
    .notNull()
    .$defaultFn(() => new Date().toISOString()),
});
```

**Step 2: Add user_lists junction table**

```typescript
export const userLists = sqliteTable("user_lists", {
  userId: integer("user_id")
    .notNull()
    .references(() => users.id),
  listId: integer("list_id")
    .notNull()
    .references(() => lists.id),
});
```

**Step 3: Add userId to events table**

```typescript
// Add to existing events table definition:
userId: integer("user_id").references(() => users.id),
```

**Step 4: Generate migration**

Run: `bunx drizzle-kit generate --name=add-users`

**Step 5: Commit**

```
git add src/db/schema.ts drizzle/
git commit -m "schema: add users, user_lists tables and userId on events"
```

---

### Task 2: Auth system rewrite

**Files:**
- Rewrite: `src/auth.ts`
- Modify: `src/config.ts`
- Test: `tests/auth.test.ts`

**Step 1: Update config to add owner bootstrap vars**

Add to Config type and loadConfig:
```typescript
ownerEmail: string;
ownerPassword: string;
```

These use `process.env.OWNER_EMAIL ?? ""` and `process.env.OWNER_PASSWORD ?? ""` (not required, empty means skip bootstrap).

Remove `authPassword` from Config (replaced by per-user passwords).

Keep `apiToken` for the API bearer auth.

**Step 2: Rewrite src/auth.ts**

Replace in-memory session map with user-aware sessions:

```typescript
import { getCookie, setCookie, deleteCookie } from "hono/cookie";
import { bearerAuth } from "hono/bearer-auth";
import { createMiddleware } from "hono/factory";
import { eq } from "drizzle-orm";
import type { Db } from "./db";
import { schema } from "./db";

type Session = { userId: number; expiry: number };
const sessions = new Map<string, Session>();

export function createSession(userId: number): string {
  const token = crypto.randomUUID();
  sessions.set(token, { userId, expiry: Date.now() + 24 * 60 * 60 * 1000 });
  return token;
}

export function destroySession(token: string) {
  sessions.delete(token);
}

function getSession(token: string): Session | null {
  const session = sessions.get(token);
  if (!session) return null;
  if (Date.now() > session.expiry) {
    sessions.delete(token);
    return null;
  }
  return session;
}

// Middleware: load user from session, attach to context
export function adminAuth(db: Db) {
  return createMiddleware(async (c, next) => {
    const token = getCookie(c, "session");
    if (!token) return c.redirect("/admin/login");
    const session = getSession(token);
    if (!session) return c.redirect("/admin/login");
    const user = db
      .select()
      .from(schema.users)
      .where(eq(schema.users.id, session.userId))
      .get();
    if (!user) return c.redirect("/admin/login");
    c.set("user", user);
    return next();
  });
}

// Middleware: require specific roles
export function requireRole(...roles: string[]) {
  return createMiddleware(async (c, next) => {
    const user = c.get("user");
    if (!roles.includes(user.role)) {
      return c.text("Forbidden", 403);
    }
    return next();
  });
}

// Middleware: require access to a specific list
export function requireListAccess(db: Db, getListId: (c: any) => number) {
  return createMiddleware(async (c, next) => {
    const user = c.get("user");
    if (user.role === "owner" || user.role === "admin") return next();
    const listId = getListId(c);
    const access = db
      .select()
      .from(schema.userLists)
      .where(
        and(
          eq(schema.userLists.userId, user.id),
          eq(schema.userLists.listId, listId),
        ),
      )
      .get();
    if (!access) return c.text("Forbidden", 403);
    return next();
  });
}

// Helper: get list IDs accessible to a user
export function getAccessibleListIds(db: Db, user: typeof schema.users.$inferSelect): number[] | "all" {
  if (user.role === "owner" || user.role === "admin") return "all";
  return db
    .select({ listId: schema.userLists.listId })
    .from(schema.userLists)
    .where(eq(schema.userLists.userId, user.id))
    .all()
    .map((r) => r.listId);
}

export function apiAuth(token: string) {
  return bearerAuth({ token });
}
```

**Step 3: Add owner bootstrap function**

Create `src/bootstrap.ts`:

```typescript
import type { Db } from "./db";
import { schema } from "./db";
import type { Config } from "./config";

export async function bootstrapOwner(db: Db, config: Config) {
  if (!config.ownerEmail || !config.ownerPassword) return;
  const existing = db.select().from(schema.users).all();
  if (existing.length > 0) return; // already have users
  const passwordHash = await Bun.password.hash(config.ownerPassword);
  db.insert(schema.users)
    .values({
      email: config.ownerEmail,
      name: "Owner",
      passwordHash,
      role: "owner",
    })
    .run();
  console.log(`Bootstrapped owner account: ${config.ownerEmail}`);
}
```

**Step 4: Update tests**

Rewrite `tests/auth.test.ts` to test:
- `createSession(userId)` returns token, session stores userId
- `destroySession` invalidates
- `adminAuth` middleware redirects without session, allows with valid session
- `requireRole` returns 403 for wrong role, allows correct role
- `getAccessibleListIds` returns "all" for owner/admin, list of IDs for member

**Step 5: Run tests**

Run: `bun test tests/auth.test.ts`

**Step 6: Commit**

```
git add src/auth.ts src/bootstrap.ts src/config.ts tests/auth.test.ts
git commit -m "rewrite auth: user-aware sessions, role middleware, owner bootstrap"
```

---

### Task 3: Login page — email + password

**Files:**
- Modify: `src/routes/admin.tsx` (login GET/POST handlers)

**Step 1: Update login form**

Replace single password field with email + password fields.

**Step 2: Update login POST handler**

- Look up user by email
- Verify password with `Bun.password.verify(password, user.passwordHash)`
- Create session with `createSession(user.id)`
- Set cookie, redirect to /admin/

**Step 3: Update logout handler**

No change needed, `destroySession` works the same.

**Step 4: Update adminAuth middleware usage**

`adminAuth` now takes `db` parameter. Update the middleware application in `adminRoutes`.

**Step 5: Commit**

```
git commit -m "login: email + password, user-aware sessions"
```

---

### Task 4: Wire user context through admin routes

**Files:**
- Modify: `src/routes/admin.tsx` (all route handlers)

**Step 1: Access user in route handlers**

Every handler can now do `const user = c.get("user")` to get the logged-in user.

**Step 2: Update logEvent calls**

Every `logEvent(db, { type: ..., detail: ... })` call gains `userId: user.id`.

**Step 3: Update activity feed display**

Query user name for each event and display "Jack created subscriber..." instead of just "admin created subscriber...".

**Step 4: Update nav to show logged-in user**

Show user name/email in the nav bar next to the logout button.

**Step 5: Commit**

```
git commit -m "wire user context: events attributed to users, nav shows current user"
```

---

### Task 5: Filtered views for members

**Files:**
- Modify: `src/routes/admin.tsx`

**Step 1: Filter list queries**

Use `getAccessibleListIds(db, user)` to scope queries:
- If "all": no filter (existing behavior)
- If array: add `inArray(schema.lists.id, listIds)` to WHERE clauses

**Step 2: Scope these pages:**

- Dashboard: stats filtered to accessible lists
- Lists index: only accessible lists
- Subscribers: only subscribers on accessible lists
- Campaigns: only campaigns on accessible lists
- Inbound: only messages linked to accessible campaigns
- Activity: only events for accessible lists/campaigns

**Step 3: Hide UI elements members can't use**

- Hide "New List" button for members
- Hide "Users" nav link for members
- Hide delete list button for members

**Step 4: Add role checks to mutation routes**

- POST /lists/new: requireRole("owner", "admin")
- POST /lists/:id/delete: requireRole("owner", "admin")
- POST /users/*: requireRole("owner", "admin")

**Step 5: Commit**

```
git commit -m "filtered views: members see only their assigned lists"
```

---

### Task 6: Users management pages

**Files:**
- Modify: `src/routes/admin.tsx`

**Step 1: Add Users nav link** (visible to owner/admin only)

**Step 2: Users list page (`GET /users`)**

Table: email, name, role, created date. "Invite User" button.

**Step 3: Invite user page (`GET /users/new`)**

Form: email, name, temporary password, role (select: admin/member), list checkboxes (shown when member selected, via JS toggle).

**Step 4: Invite user POST (`POST /users/new`)**

Hash password, insert user, insert user_lists for selected lists, log event.

**Step 5: User detail page (`GET /users/:id`)**

Edit name, role, list assignments. Reset password field. Delete button.

**Step 6: User edit POST (`POST /users/:id/edit`)**

Update user fields. If password provided, hash and update. Sync user_lists.

**Step 7: User delete POST (`POST /users/:id/delete`)**

Delete user_lists, nullify events.userId, delete user.

**Step 8: Commit**

```
git commit -m "users management: invite, edit, delete, list assignments"
```

---

### Task 7: E2E tests for user system

**Files:**
- Create: `tests/users.test.ts`
- Modify: `tests/e2e.test.ts`

**Step 1: Test owner bootstrap**

- Empty DB + env vars -> owner created
- Non-empty DB + env vars -> no duplicate

**Step 2: Test login flow via Hono**

- POST /admin/login with correct email/password -> redirect + session cookie
- POST /admin/login with wrong password -> error

**Step 3: Test role-based access**

- Member accessing /admin/users -> 403
- Member accessing other member's list -> 403
- Member accessing their own list -> 200
- Owner accessing everything -> 200

**Step 4: Test invite flow**

- Owner creates member with list assignment
- Member logs in, sees only assigned list

**Step 5: Update existing e2e tests**

Existing tests use `AUTH_PASSWORD` for login. Update to bootstrap an owner and use email+password.

**Step 6: Run full suite**

Run: `bun test`

**Step 7: Commit**

```
git commit -m "tests: user accounts, RBAC, login flow, filtered access"
```

---

### Task 8: Config migration and cleanup

**Files:**
- Modify: `src/config.ts`
- Modify: `src/index.ts`
- Modify: `hosts/mug/secrets/lists.enc.yaml` (infra repo)

**Step 1: Update index.ts**

Call `bootstrapOwner(db, config)` after `createDb` but before starting the server.

**Step 2: Update SOPS secrets**

Replace `AUTH_PASSWORD` with `OWNER_EMAIL` and `OWNER_PASSWORD`.

**Step 3: Update Dockerfile / compose if needed**

No changes expected, env vars are passed through.

**Step 4: Commit both repos**

```
# lists repo
git commit -m "wire bootstrap into startup, remove AUTH_PASSWORD"

# infra repo
git commit -m "update lists secrets: OWNER_EMAIL + OWNER_PASSWORD replace AUTH_PASSWORD"
```

---

### Task 9: Final verification

**Step 1: Run full test suite**

Run: `bun test`
Expected: All tests pass.

**Step 2: Docker build**

Run: `docker build -t lists:test .`
Expected: Builds clean.

**Step 3: Local smoke test**

```
docker run --rm -p 8081:8080 \
  -e SQS_QUEUE_URL=fake -e S3_BUCKET=fake \
  -e API_TOKEN=test -e BASE_URL=http://localhost:8081 \
  -e OWNER_EMAIL=admin@example.com -e OWNER_PASSWORD=test123 \
  lists:test
```

- Visit /admin/login, login with owner credentials
- Verify dashboard loads
- Create a member user, assign to a list
- Log out, log in as member, verify scoped view

**Step 4: Push and deploy**

```
git push origin main
```

# mail-ingest Go Service Design

> **SUPERSEDED** by `docs/plans/2026-03-09-lists-design.md`. The mail-ingest service has been absorbed into the `lists` newsletter service.

## Goal

A small Go service that consumes SES inbound email metadata from SQS, stores it in SQLite, and serves a password-protected web UI for browsing listmonk reply tracking.

## Environment Variables

| Var | Example |
|-----|---------|
| `AWS_ACCESS_KEY_ID` | IAM user credential |
| `AWS_SECRET_ACCESS_KEY` | IAM user credential |
| `AWS_REGION` | `us-east-1` |
| `SQS_QUEUE_URL` | `https://sqs.us-east-1.amazonaws.com/...` |
| `S3_BUCKET` | `ses-inbound-email` |
| `AUTH_PASSWORD` | shared password for login |
| `DB_PATH` | `/data/mail-ingest.db` |

## SQLite Schema

```sql
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id TEXT UNIQUE NOT NULL,
    timestamp TEXT NOT NULL,
    source TEXT NOT NULL,
    from_addrs TEXT NOT NULL,    -- JSON array
    to_addrs TEXT NOT NULL,      -- JSON array
    subject TEXT NOT NULL,
    spam_verdict TEXT,
    virus_verdict TEXT,
    spf_verdict TEXT,
    dkim_verdict TEXT,
    dmarc_verdict TEXT,
    s3_key TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

## HTTP Routes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/login` | Login form |
| POST | `/login` | Validate password, set session cookie |
| GET | `/` | Message list (paginated, newest first) |
| GET | `/message/:id/raw` | Redirect to presigned S3 URL for .eml |
| POST | `/logout` | Clear session |

## SQS Poller

- Long-polls with `WaitTimeSeconds: 20` in a loop
- On message: parse JSON body, INSERT into SQLite (ignore duplicates on `message_id`), delete from queue
- On error: log and continue (message returns to queue after visibility timeout, DLQ catches persistent failures)

## Project Structure

```
mail-ingest/
├── main.go              # entry point, wires up poller + server
├── poller.go            # SQS long-poll loop
├── db.go                # SQLite init + queries
├── handlers.go          # HTTP handlers
├── auth.go              # session/cookie auth middleware
├── templates/
│   ├── login.html
│   ├── messages.html
│   └── layout.html
├── Dockerfile
├── go.mod
└── go.sum
```

## Dependencies

- `github.com/aws/aws-sdk-go-v2` (SQS + S3 presigner)
- `modernc.org/sqlite` (pure Go SQLite, no CGO)
- stdlib for HTTP, templates, crypto

## Dockerfile

Multi-stage: build with `golang:1.23-alpine`, run on `alpine:3.19`. Copy binary + `templates/` dir.

## CI

GitHub Actions: build + push to GHCR on push to `main`. Watchtower on mug auto-deploys.

## Out of Scope

- MIME parsing / attachment extraction
- Reply-to-listmonk campaign linking
- Any infra provisioning (covered by the separate mail-plan.md)

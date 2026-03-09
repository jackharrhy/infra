# mail-ingest Part 2: Threaded Replies Implementation Plan

> **SUPERSEDED** by `docs/plans/2026-03-09-lists-design.md`. The mail-ingest service has been absorbed into the `lists` newsletter service.

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add the ability to reply to inbound emails from the mail-ingest web UI, with correct threading so replies appear in the subscriber's existing email thread.

**Architecture:** Fetch the raw `.eml` from S3 to extract `Message-ID` headers, present a reply form in the UI, send via SES `SendRawEmail` with correct `In-Reply-To` / `References` headers so the subscriber sees a threaded conversation.

**Tech Stack:** Go, AWS SDK v2 (SES + S3), `net/mail` (stdlib header parsing)

**Prerequisite:** Complete `docs/plans/2026-03-09-mail-ingest-plan.md` (part 1) first.

**Infra prerequisite:** The `mail-ingest` IAM user (from `docs/plans/mail-plan.md` task 6) needs `ses:SendRawEmail` added to its policy.

---

### Task 1: Add SES send permission to the mail-ingest IAM user

This task is in the **infra repo** (`jackharrhy/infra`), not the mail-ingest repo.

**Files:**
- Modify: `aws/index.ts`

**Step 1: Add `ses:SendRawEmail` to the mail-ingest user policy**

In `aws/index.ts`, find the `mail-ingest-policy` UserPolicy and add a third statement:

```typescript
{
  Sid: "SESSend",
  Effect: "Allow",
  Action: ["ses:SendRawEmail"],
  Resource: "*",
},
```

The full policy `Statement` array becomes:

```typescript
[
  {
    Sid: "SQSRead",
    Effect: "Allow",
    Action: [
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
      "sqs:ChangeMessageVisibility",
    ],
    Resource: [queueArn, dlqArn],
  },
  {
    Sid: "S3Read",
    Effect: "Allow",
    Action: ["s3:GetObject"],
    Resource: `${bucketArn}/*`,
  },
  {
    Sid: "SESSend",
    Effect: "Allow",
    Action: ["ses:SendRawEmail"],
    Resource: "*",
  },
]
```

**Step 2: Verify with Pulumi preview**

Run: `pulumi preview` (from `aws/` directory)
Expected: 1 resource to update (UserPolicy). No other changes.

**Step 3: Deploy**

Run: `pulumi up --yes` (from `aws/` directory)
Expected: Policy updated.

**Step 4: Commit**

```bash
git add aws/index.ts
git commit -m "feat: add SES send permission to mail-ingest IAM user"
```

---

### Task 2: Add a new env var and update config

Back in the **mail-ingest repo**.

**Files:**
- Modify: `config.go`

**Step 1: Add `REPLY_FROM_DOMAIN` to Config**

The service needs to know which domain to send replies from. Add to the `Config` struct and `loadConfig`:

```go
type Config struct {
	AWSRegion      string
	SQSQueueURL    string
	S3Bucket       string
	AuthPassword   string
	DBPath         string
	ReplyFromDomain string
}

func loadConfig() Config {
	cfg := Config{
		AWSRegion:       os.Getenv("AWS_REGION"),
		SQSQueueURL:     os.Getenv("SQS_QUEUE_URL"),
		S3Bucket:        os.Getenv("S3_BUCKET"),
		AuthPassword:    os.Getenv("AUTH_PASSWORD"),
		DBPath:          os.Getenv("DB_PATH"),
		ReplyFromDomain: os.Getenv("REPLY_FROM_DOMAIN"),
	}
	if cfg.SQSQueueURL == "" {
		log.Fatal("SQS_QUEUE_URL is required")
	}
	if cfg.S3Bucket == "" {
		log.Fatal("S3_BUCKET is required")
	}
	if cfg.AuthPassword == "" {
		log.Fatal("AUTH_PASSWORD is required")
	}
	if cfg.DBPath == "" {
		cfg.DBPath = "mail-ingest.db"
	}
	if cfg.AWSRegion == "" {
		cfg.AWSRegion = "us-east-1"
	}
	if cfg.ReplyFromDomain == "" {
		cfg.ReplyFromDomain = "jackharrhy.dev"
	}
	return cfg
}
```

**Step 2: Verify it compiles**

Run: `go build ./...`
Expected: No errors.

**Step 3: Commit**

```bash
git add config.go
git commit -m "feat: add REPLY_FROM_DOMAIN config"
```

---

### Task 3: Add replies table to the database

**Files:**
- Modify: `db.go`

**Step 1: Add schema for sent replies**

Add a second table to the `schema` const:

```go
const schema = `
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id TEXT UNIQUE NOT NULL,
    timestamp TEXT NOT NULL,
    source TEXT NOT NULL,
    from_addrs TEXT NOT NULL,
    to_addrs TEXT NOT NULL,
    subject TEXT NOT NULL,
    spam_verdict TEXT,
    virus_verdict TEXT,
    spf_verdict TEXT,
    dkim_verdict TEXT,
    dmarc_verdict TEXT,
    s3_key TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS replies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER NOT NULL REFERENCES messages(id),
    ses_message_id TEXT,
    from_addr TEXT NOT NULL,
    to_addr TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    in_reply_to TEXT,
    sent_at TEXT NOT NULL DEFAULT (datetime('now'))
);
`
```

**Step 2: Add query functions for replies**

Append to `db.go`:

```go
type Reply struct {
	ID           int
	MessageID    int
	SESMessageID *string
	FromAddr     string
	ToAddr       string
	Subject      string
	Body         string
	InReplyTo    *string
	SentAt       string
}

func insertReply(db *sql.DB, r Reply) (int64, error) {
	result, err := db.Exec(`
		INSERT INTO replies (message_id, ses_message_id, from_addr, to_addr, subject, body, in_reply_to)
		VALUES (?, ?, ?, ?, ?, ?, ?)`,
		r.MessageID, r.SESMessageID, r.FromAddr, r.ToAddr, r.Subject, r.Body, r.InReplyTo,
	)
	if err != nil {
		return 0, err
	}
	return result.LastInsertId()
}

func getRepliesForMessage(db *sql.DB, messageID int) ([]Reply, error) {
	rows, err := db.Query(`
		SELECT id, message_id, ses_message_id, from_addr, to_addr, subject, body, in_reply_to, sent_at
		FROM replies WHERE message_id = ? ORDER BY sent_at ASC`, messageID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var replies []Reply
	for rows.Next() {
		var r Reply
		if err := rows.Scan(
			&r.ID, &r.MessageID, &r.SESMessageID, &r.FromAddr, &r.ToAddr,
			&r.Subject, &r.Body, &r.InReplyTo, &r.SentAt,
		); err != nil {
			return nil, err
		}
		replies = append(replies, r)
	}
	return replies, rows.Err()
}
```

**Step 3: Verify it compiles**

Run: `go build ./...`
Expected: No errors.

**Step 4: Commit**

```bash
git add db.go
git commit -m "feat: add replies table and query functions"
```

---

### Task 4: Implement .eml header parsing

**Files:**
- Create: `email.go`

**Step 1: Write the header parser**

This fetches the raw `.eml` from S3 and extracts threading headers using `net/mail` from stdlib. No full MIME parsing -- just the headers.

```go
package main

import (
	"context"
	"fmt"
	"io"
	"net/mail"

	"github.com/aws/aws-sdk-go-v2/aws"
	awsS3 "github.com/aws/aws-sdk-go-v2/service/s3"
)

type EmailHeaders struct {
	MessageID  string
	InReplyTo  string
	References string
	Subject    string
	From       string
	To         string
}

func fetchEmailHeaders(ctx context.Context, awsCfg aws.Config, bucket, key string) (*EmailHeaders, error) {
	client := awsS3.NewFromConfig(awsCfg)

	result, err := client.GetObject(ctx, &awsS3.GetObjectInput{
		Bucket: aws.String(bucket),
		Key:    aws.String(key),
	})
	if err != nil {
		return nil, fmt.Errorf("failed to get S3 object: %w", err)
	}
	defer result.Body.Close()

	msg, err := mail.ReadMessage(result.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to parse email headers: %w", err)
	}

	// Discard the body -- we only need headers
	io.Copy(io.Discard, msg.Body)

	return &EmailHeaders{
		MessageID:  msg.Header.Get("Message-ID"),
		InReplyTo:  msg.Header.Get("In-Reply-To"),
		References: msg.Header.Get("References"),
		Subject:    msg.Header.Get("Subject"),
		From:       msg.Header.Get("From"),
		To:         msg.Header.Get("To"),
	}, nil
}
```

**Step 2: Verify it compiles**

Run: `go build ./...`
Expected: No errors.

**Step 3: Commit**

```bash
git add email.go
git commit -m "feat: add .eml header parser via S3"
```

---

### Task 5: Implement SES email sending

**Files:**
- Create: `sender.go`

**Step 1: Write the send function**

This constructs a raw RFC 2822 email with correct threading headers and sends it via SES `SendRawEmail`.

```go
package main

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/service/sesv2"
	"github.com/aws/aws-sdk-go-v2/service/sesv2/types"
)

type OutboundEmail struct {
	From       string
	To         string
	Subject    string
	Body       string
	InReplyTo  string
	References string
}

func sendReplyEmail(ctx context.Context, awsCfg aws.Config, email OutboundEmail) (string, error) {
	client := sesv2.NewFromConfig(awsCfg)

	var raw strings.Builder
	raw.WriteString(fmt.Sprintf("From: %s\r\n", email.From))
	raw.WriteString(fmt.Sprintf("To: %s\r\n", email.To))
	raw.WriteString(fmt.Sprintf("Subject: %s\r\n", email.Subject))
	raw.WriteString(fmt.Sprintf("Date: %s\r\n", time.Now().UTC().Format(time.RFC1123Z)))
	raw.WriteString("MIME-Version: 1.0\r\n")
	raw.WriteString("Content-Type: text/plain; charset=UTF-8\r\n")

	if email.InReplyTo != "" {
		raw.WriteString(fmt.Sprintf("In-Reply-To: %s\r\n", email.InReplyTo))
	}
	if email.References != "" {
		raw.WriteString(fmt.Sprintf("References: %s\r\n", email.References))
	}

	raw.WriteString("\r\n")
	raw.WriteString(email.Body)

	result, err := client.SendEmail(ctx, &sesv2.SendEmailInput{
		Content: &types.EmailContent{
			Raw: &types.RawMessage{
				Data: []byte(raw.String()),
			},
		},
	})
	if err != nil {
		return "", fmt.Errorf("SES send failed: %w", err)
	}

	messageID := ""
	if result.MessageId != nil {
		messageID = *result.MessageId
	}
	return messageID, nil
}
```

**Step 2: Verify it compiles**

Run: `go get github.com/aws/aws-sdk-go-v2/service/sesv2 && go build ./...`
Expected: No errors.

**Step 3: Commit**

```bash
git add sender.go go.mod go.sum
git commit -m "feat: implement SES email sending with threading headers"
```

---

### Task 6: Add message detail page and reply form

**Files:**
- Create: `templates/message.html`
- Modify: `templates/messages.html`
- Modify: `handlers.go`

**Step 1: Create `templates/message.html`**

```html
{{define "content"}}
<nav>
    <h1>Message #{{.Message.ID}}</h1>
    <a href="/">Back to list</a>
</nav>

<table>
    <tr><th>From</th><td>{{.Message.Source}}</td></tr>
    <tr><th>To</th><td>{{.Message.ToAddrs}}</td></tr>
    <tr><th>Subject</th><td>{{.Message.Subject}}</td></tr>
    <tr><th>Date</th><td>{{.Message.Timestamp}}</td></tr>
    <tr><th>SPF</th><td class="{{verdictClass .Message.SPFVerdict}}">{{deref .Message.SPFVerdict}}</td></tr>
    <tr><th>DKIM</th><td class="{{verdictClass .Message.DKIMVerdict}}">{{deref .Message.DKIMVerdict}}</td></tr>
    <tr><th>DMARC</th><td class="{{verdictClass .Message.DMARCVerdict}}">{{deref .Message.DMARCVerdict}}</td></tr>
    <tr><th>Spam</th><td class="{{verdictClass .Message.SpamVerdict}}">{{deref .Message.SpamVerdict}}</td></tr>
    {{if .Message.S3Key}}<tr><th>Raw</th><td><a href="/message/{{.Message.ID}}/raw">Download .eml</a></td></tr>{{end}}
</table>

{{if .Replies}}
<h2>Replies sent</h2>
<table>
    <thead><tr><th>Date</th><th>From</th><th>Subject</th></tr></thead>
    <tbody>
    {{range .Replies}}
    <tr>
        <td>{{.SentAt}}</td>
        <td>{{.FromAddr}}</td>
        <td>{{.Subject}}</td>
    </tr>
    {{end}}
    </tbody>
</table>
{{end}}

<h2>Send reply</h2>
{{if .Error}}<p style="color: red;">{{.Error}}</p>{{end}}
{{if .Success}}<p style="color: green;">{{.Success}}</p>{{end}}
<form method="POST" action="/message/{{.Message.ID}}/reply">
    <label for="from">From</label>
    <input type="text" id="from" name="from" value="{{.DefaultFrom}}" required style="width:100%;max-width:500px;">
    <label for="body">Reply</label>
    <textarea id="body" name="body" rows="10" required style="width:100%;max-width:500px;">{{.DraftBody}}</textarea>
    <button type="submit">Send reply</button>
</form>
{{end}}
```

**Step 2: Add a link from the messages list to the detail page**

In `templates/messages.html`, change the subject column from plain text to a link:

```html
<td><a href="/message/{{.ID}}">{{.Subject}}</a></td>
```

**Step 3: Add detail and reply handlers to `handlers.go`**

Add new routes in `newRouter`:

```go
func newRouter(db *sql.DB, awsCfg aws.Config, cfg Config) http.Handler {
	mux := http.NewServeMux()

	mux.HandleFunc("GET /login", handleLoginPage)
	mux.HandleFunc("POST /login", handleLogin(cfg.AuthPassword))
	mux.HandleFunc("POST /logout", handleLogout)

	protected := http.NewServeMux()
	protected.HandleFunc("GET /", handleMessages(db))
	protected.HandleFunc("GET /message/{id}", handleMessageDetail(db, awsCfg, cfg))
	protected.HandleFunc("POST /message/{id}/reply", handleSendReply(db, awsCfg, cfg))
	protected.HandleFunc("GET /message/{id}/raw", handleRawEmail(db, awsCfg, cfg.S3Bucket))

	mux.Handle("/", requireAuth(cfg.AuthPassword, protected))
	return mux
}
```

Add the handler functions:

```go
type messageDetailData struct {
	Message     *Message
	Replies     []Reply
	DefaultFrom string
	DraftBody   string
	Error       string
	Success     string
}

func handleMessageDetail(db *sql.DB, awsCfg aws.Config, cfg Config) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		id, err := strconv.Atoi(r.PathValue("id"))
		if err != nil {
			http.Error(w, "bad id", 400)
			return
		}

		msg, err := getMessage(db, id)
		if err != nil {
			log.Printf("get message error: %v", err)
			http.Error(w, "internal error", 500)
			return
		}
		if msg == nil {
			http.Error(w, "not found", 404)
			return
		}

		replies, err := getRepliesForMessage(db, id)
		if err != nil {
			log.Printf("get replies error: %v", err)
			http.Error(w, "internal error", 500)
			return
		}

		// Determine "from" address: use the To address from the inbound email
		// e.g. if they sent to plow@reply.jackharrhy.dev, reply from plow@jackharrhy.dev
		defaultFrom := deriveFromAddress(msg.ToAddrs, cfg.ReplyFromDomain)

		data := messageDetailData{
			Message:     msg,
			Replies:     replies,
			DefaultFrom: defaultFrom,
		}
		tmpl.ExecuteTemplate(w, "layout", data)
	}
}

func handleSendReply(db *sql.DB, awsCfg aws.Config, cfg Config) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		id, err := strconv.Atoi(r.PathValue("id"))
		if err != nil {
			http.Error(w, "bad id", 400)
			return
		}

		msg, err := getMessage(db, id)
		if err != nil || msg == nil {
			http.Error(w, "not found", 404)
			return
		}

		fromAddr := r.FormValue("from")
		body := r.FormValue("body")
		if fromAddr == "" || body == "" {
			renderDetailWithError(w, db, awsCfg, cfg, msg, "From and body are required.", body)
			return
		}

		// Fetch original email headers from S3 for threading
		var inReplyTo, references string
		if msg.S3Key != nil && *msg.S3Key != "" {
			headers, err := fetchEmailHeaders(r.Context(), awsCfg, cfg.S3Bucket, *msg.S3Key)
			if err != nil {
				log.Printf("failed to fetch email headers: %v", err)
				// Non-fatal -- send without threading
			} else {
				inReplyTo = headers.MessageID
				if headers.References != "" {
					references = headers.References + " " + headers.MessageID
				} else {
					references = headers.MessageID
				}
			}
		}

		subject := msg.Subject
		if !strings.HasPrefix(strings.ToLower(subject), "re:") {
			subject = "Re: " + subject
		}

		sesMessageID, err := sendReplyEmail(r.Context(), awsCfg, OutboundEmail{
			From:       fromAddr,
			To:         msg.Source,
			Subject:    subject,
			Body:       body,
			InReplyTo:  inReplyTo,
			References: references,
		})
		if err != nil {
			log.Printf("failed to send reply: %v", err)
			renderDetailWithError(w, db, awsCfg, cfg, msg, "Failed to send: "+err.Error(), body)
			return
		}

		insertReply(db, Reply{
			MessageID:    msg.ID,
			SESMessageID: strPtr(sesMessageID),
			FromAddr:     fromAddr,
			ToAddr:       msg.Source,
			Subject:      subject,
			Body:         body,
			InReplyTo:    strPtr(inReplyTo),
		})

		log.Printf("sent reply to %s for message %d (SES ID: %s)", msg.Source, msg.ID, sesMessageID)

		http.Redirect(w, r, fmt.Sprintf("/message/%d", id), http.StatusSeeOther)
	}
}

func renderDetailWithError(w http.ResponseWriter, db *sql.DB, awsCfg aws.Config, cfg Config, msg *Message, errMsg, draftBody string) {
	replies, _ := getRepliesForMessage(db, msg.ID)
	defaultFrom := deriveFromAddress(msg.ToAddrs, cfg.ReplyFromDomain)
	data := messageDetailData{
		Message:     msg,
		Replies:     replies,
		DefaultFrom: defaultFrom,
		DraftBody:   draftBody,
		Error:       errMsg,
	}
	tmpl.ExecuteTemplate(w, "layout", data)
}

// deriveFromAddress takes the JSON-encoded To addresses from the inbound
// message and rewrites the domain. e.g. ["plow@reply.jackharrhy.dev"]
// becomes plow@jackharrhy.dev.
func deriveFromAddress(toAddrsJSON, fromDomain string) string {
	var addrs []string
	json.Unmarshal([]byte(toAddrsJSON), &addrs)
	if len(addrs) == 0 {
		return ""
	}
	// Take the first address, extract the local part
	addr := addrs[0]
	if at := strings.Index(addr, "@"); at >= 0 {
		return addr[:at] + "@" + fromDomain
	}
	return addr
}
```

Note: add `"encoding/json"`, `"fmt"`, and `"strings"` to the imports in `handlers.go` if not already present.

**Step 4: Verify it compiles**

Run: `go build ./...`
Expected: No errors.

**Step 5: Commit**

```bash
git add handlers.go templates/ email.go
git commit -m "feat: add message detail page with threaded reply form"
```

---

### Task 7: Update infra secrets and test end-to-end

Back in the **infra repo** (`jackharrhy/infra`).

**Files:**
- Modify: `hosts/mug/secrets/mail-ingest.env`

**Step 1: Add the new env var to the secrets file**

Add to `hosts/mug/secrets/mail-ingest.env` (before encryption):

```
REPLY_FROM_DOMAIN=jackharrhy.dev
```

Re-encrypt: `sops --encrypt --in-place hosts/mug/secrets/mail-ingest.env`

**Step 2: Deploy updated mail-ingest to mug**

The new image will be picked up by watchtower automatically once pushed to GHCR. Or manually:

Run: `docker compose pull mail-ingest && docker compose up -d mail-ingest` (on mug)

**Step 3: Test the reply flow**

1. Open `replies.jackharrhy.dev`, log in
2. Click on an existing inbound message
3. Type a reply and hit "Send reply"
4. Check the recipient's inbox -- the reply should appear in the same thread as the original

**Step 4: Commit (if any adjustments were made)**

```bash
git add hosts/mug/secrets/mail-ingest.env
git commit -m "feat: add REPLY_FROM_DOMAIN to mail-ingest secrets"
```

# mail-ingest Implementation Plan

> **SUPERSEDED** by `docs/plans/2026-03-09-lists-design.md`. The mail-ingest service has been absorbed into the `lists` newsletter service.

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Go service that polls SQS for inbound email metadata, stores it in SQLite, and serves a password-protected web UI for browsing listmonk replies.

**Architecture:** Single binary, two goroutines -- one long-polls SQS in a loop, one serves HTTP. SQLite for persistence, html/template for views, AWS SDK v2 for SQS/S3.

**Tech Stack:** Go 1.23, `modernc.org/sqlite`, `github.com/aws/aws-sdk-go-v2`, stdlib `net/http` + `html/template`

**Design doc:** `docs/plans/2026-03-09-mail-ingest-design.md`

**Part 2 (threaded replies):** `docs/plans/2026-03-09-mail-ingest-replies-plan.md`

**Env vars the service expects:**

| Var | Purpose |
|-----|---------|
| `AWS_ACCESS_KEY_ID` | IAM credentials for SQS + S3 |
| `AWS_SECRET_ACCESS_KEY` | IAM credentials for SQS + S3 |
| `AWS_REGION` | AWS region (`us-east-1`) |
| `SQS_QUEUE_URL` | SQS queue to poll |
| `S3_BUCKET` | Bucket containing raw `.eml` files |
| `AUTH_PASSWORD` | Password for web UI login |
| `DB_PATH` | SQLite database file path |

---

### Task 1: Scaffold the project

**Files:**
- Create: `go.mod`
- Create: `main.go`
- Create: `Dockerfile`
- Create: `.github/workflows/build.yml`

**Step 1: Initialize go module**

Run: `go mod init github.com/jackharrhy/mail-ingest`

**Step 2: Create `main.go` entry point**

```go
package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"
)

func main() {
	cfg := loadConfig()

	db, err := initDB(cfg.DBPath)
	if err != nil {
		log.Fatalf("failed to init db: %v", err)
	}
	defer db.Close()

	awsCfg := mustLoadAWSConfig(cfg)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	go pollSQS(ctx, awsCfg, cfg.SQSQueueURL, db)

	mux := newRouter(db, awsCfg, cfg)
	srv := &http.Server{
		Addr:    ":8080",
		Handler: mux,
	}

	go func() {
		log.Println("listening on :8080")
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("server error: %v", err)
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit
	log.Println("shutting down...")
	cancel()

	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer shutdownCancel()
	srv.Shutdown(shutdownCtx)
}
```

**Step 3: Create `config.go`**

```go
package main

import (
	"log"
	"os"
)

type Config struct {
	AWSRegion    string
	SQSQueueURL  string
	S3Bucket     string
	AuthPassword string
	DBPath       string
}

func loadConfig() Config {
	cfg := Config{
		AWSRegion:    os.Getenv("AWS_REGION"),
		SQSQueueURL:  os.Getenv("SQS_QUEUE_URL"),
		S3Bucket:     os.Getenv("S3_BUCKET"),
		AuthPassword: os.Getenv("AUTH_PASSWORD"),
		DBPath:       os.Getenv("DB_PATH"),
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
	return cfg
}
```

**Step 4: Create stub files**

Create empty stub files so the project compiles. Each will be filled in subsequent tasks.

`aws.go`:
```go
package main

import (
	"context"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
)

func mustLoadAWSConfig(cfg Config) aws.Config {
	awsCfg, err := config.LoadDefaultConfig(context.Background(),
		config.WithRegion(cfg.AWSRegion),
	)
	if err != nil {
		panic("failed to load AWS config: " + err.Error())
	}
	return awsCfg
}
```

`db.go`:
```go
package main

import "database/sql"

func initDB(path string) (*sql.DB, error) {
	return nil, nil
}
```

`poller.go`:
```go
package main

import (
	"context"
	"database/sql"

	"github.com/aws/aws-sdk-go-v2/aws"
)

func pollSQS(ctx context.Context, cfg aws.Config, queueURL string, db *sql.DB) {
}
```

`handlers.go`:
```go
package main

import (
	"database/sql"
	"net/http"

	"github.com/aws/aws-sdk-go-v2/aws"
)

func newRouter(db *sql.DB, awsCfg aws.Config, cfg Config) http.Handler {
	return http.NewServeMux()
}
```

`auth.go`:
```go
package main

import "net/http"

func requireAuth(password string, next http.Handler) http.Handler {
	return next
}
```

**Step 5: Add dependencies**

Run: `go get github.com/aws/aws-sdk-go-v2/config github.com/aws/aws-sdk-go-v2/service/sqs github.com/aws/aws-sdk-go-v2/service/s3 modernc.org/sqlite`

**Step 6: Verify it compiles**

Run: `go build ./...`
Expected: No errors.

**Step 7: Create Dockerfile**

```dockerfile
FROM golang:1.23-alpine AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o /mail-ingest .

FROM alpine:3.19
RUN apk add --no-cache ca-certificates
COPY --from=build /mail-ingest /mail-ingest
COPY templates/ /templates/
ENV DB_PATH=/data/mail-ingest.db
VOLUME /data
EXPOSE 8080
ENTRYPOINT ["/mail-ingest"]
```

**Step 8: Create GitHub Actions workflow**

`.github/workflows/build.yml`:

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

**Step 9: Commit**

```bash
git add -A
git commit -m "feat: scaffold mail-ingest project"
```

---

### Task 2: Implement SQLite database layer

**Files:**
- Modify: `db.go`

**Step 1: Implement `initDB` and schema migration**

```go
package main

import (
	"database/sql"
	"fmt"

	_ "modernc.org/sqlite"
)

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
`

type Message struct {
	ID           int
	MessageID    string
	Timestamp    string
	Source       string
	FromAddrs    string
	ToAddrs      string
	Subject      string
	SpamVerdict  *string
	VirusVerdict *string
	SPFVerdict   *string
	DKIMVerdict  *string
	DMARCVerdict *string
	S3Key        *string
	CreatedAt    string
}

func initDB(path string) (*sql.DB, error) {
	db, err := sql.Open("sqlite", fmt.Sprintf("file:%s?cache=shared&mode=rwc", path))
	if err != nil {
		return nil, err
	}
	if err := db.Ping(); err != nil {
		return nil, err
	}
	if _, err := db.Exec(schema); err != nil {
		return nil, err
	}
	return db, nil
}

func insertMessage(db *sql.DB, m Message) error {
	_, err := db.Exec(`
		INSERT OR IGNORE INTO messages
			(message_id, timestamp, source, from_addrs, to_addrs, subject,
			 spam_verdict, virus_verdict, spf_verdict, dkim_verdict, dmarc_verdict, s3_key)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
		m.MessageID, m.Timestamp, m.Source, m.FromAddrs, m.ToAddrs, m.Subject,
		m.SpamVerdict, m.VirusVerdict, m.SPFVerdict, m.DKIMVerdict, m.DMARCVerdict, m.S3Key,
	)
	return err
}

func listMessages(db *sql.DB, limit, offset int) ([]Message, error) {
	rows, err := db.Query(`
		SELECT id, message_id, timestamp, source, from_addrs, to_addrs, subject,
		       spam_verdict, virus_verdict, spf_verdict, dkim_verdict, dmarc_verdict,
		       s3_key, created_at
		FROM messages ORDER BY created_at DESC LIMIT ? OFFSET ?`, limit, offset)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var messages []Message
	for rows.Next() {
		var m Message
		if err := rows.Scan(
			&m.ID, &m.MessageID, &m.Timestamp, &m.Source, &m.FromAddrs, &m.ToAddrs,
			&m.Subject, &m.SpamVerdict, &m.VirusVerdict, &m.SPFVerdict, &m.DKIMVerdict,
			&m.DMARCVerdict, &m.S3Key, &m.CreatedAt,
		); err != nil {
			return nil, err
		}
		messages = append(messages, m)
	}
	return messages, rows.Err()
}

func countMessages(db *sql.DB) (int, error) {
	var count int
	err := db.QueryRow("SELECT COUNT(*) FROM messages").Scan(&count)
	return count, err
}

func getMessage(db *sql.DB, id int) (*Message, error) {
	var m Message
	err := db.QueryRow(`
		SELECT id, message_id, timestamp, source, from_addrs, to_addrs, subject,
		       spam_verdict, virus_verdict, spf_verdict, dkim_verdict, dmarc_verdict,
		       s3_key, created_at
		FROM messages WHERE id = ?`, id).Scan(
		&m.ID, &m.MessageID, &m.Timestamp, &m.Source, &m.FromAddrs, &m.ToAddrs,
		&m.Subject, &m.SpamVerdict, &m.VirusVerdict, &m.SPFVerdict, &m.DKIMVerdict,
		&m.DMARCVerdict, &m.S3Key, &m.CreatedAt,
	)
	if err == sql.ErrNoRows {
		return nil, nil
	}
	return &m, err
}
```

**Step 2: Verify it compiles**

Run: `go build ./...`
Expected: No errors.

**Step 3: Commit**

```bash
git add db.go
git commit -m "feat: implement SQLite database layer"
```

---

### Task 3: Implement SQS poller

**Files:**
- Modify: `poller.go`

**Step 1: Implement the poll loop**

```go
package main

import (
	"context"
	"database/sql"
	"encoding/json"
	"log"
	"strings"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/service/sqs"
)

type SQSPayload struct {
	MessageID    string   `json:"messageId"`
	Timestamp    string   `json:"timestamp"`
	Source       string   `json:"source"`
	From         []string `json:"from"`
	To           []string `json:"to"`
	Subject      string   `json:"subject"`
	SpamVerdict  string   `json:"spamVerdict"`
	VirusVerdict string   `json:"virusVerdict"`
	SPFVerdict   string   `json:"spfVerdict"`
	DKIMVerdict  string   `json:"dkimVerdict"`
	DMARCVerdict string   `json:"dmarcVerdict"`
	Action       struct {
		Type            string `json:"type"`
		BucketName      string `json:"bucketName"`
		ObjectKeyPrefix string `json:"objectKeyPrefix"`
		ObjectKey       string `json:"objectKey"`
	} `json:"action"`
}

func pollSQS(ctx context.Context, awsCfg aws.Config, queueURL string, db *sql.DB) {
	client := sqs.NewFromConfig(awsCfg)
	log.Printf("polling SQS queue: %s", queueURL)

	for {
		select {
		case <-ctx.Done():
			log.Println("SQS poller shutting down")
			return
		default:
		}

		result, err := client.ReceiveMessage(ctx, &sqs.ReceiveMessageInput{
			QueueUrl:            aws.String(queueURL),
			MaxNumberOfMessages: 10,
			WaitTimeSeconds:     20,
		})
		if err != nil {
			if ctx.Err() != nil {
				return
			}
			log.Printf("SQS receive error: %v", err)
			time.Sleep(5 * time.Second)
			continue
		}

		for _, msg := range result.Messages {
			var payload SQSPayload
			if err := json.Unmarshal([]byte(*msg.Body), &payload); err != nil {
				log.Printf("failed to parse SQS message: %v", err)
				continue
			}

			fromJSON, _ := json.Marshal(payload.From)
			toJSON, _ := json.Marshal(payload.To)

			s3Key := payload.Action.ObjectKey
			if s3Key == "" && payload.Action.ObjectKeyPrefix != "" {
				s3Key = payload.Action.ObjectKeyPrefix + payload.MessageID
			}

			m := Message{
				MessageID:    payload.MessageID,
				Timestamp:    payload.Timestamp,
				Source:       payload.Source,
				FromAddrs:    string(fromJSON),
				ToAddrs:      string(toJSON),
				Subject:      payload.Subject,
				SpamVerdict:  strPtr(payload.SpamVerdict),
				VirusVerdict: strPtr(payload.VirusVerdict),
				SPFVerdict:   strPtr(payload.SPFVerdict),
				DKIMVerdict:  strPtr(payload.DKIMVerdict),
				DMARCVerdict: strPtr(payload.DMARCVerdict),
				S3Key:        strPtr(s3Key),
			}

			if err := insertMessage(db, m); err != nil {
				log.Printf("failed to insert message %s: %v", payload.MessageID, err)
				continue
			}

			log.Printf("stored message %s from %s: %s",
				payload.MessageID, strings.Join(payload.From, ", "), payload.Subject)

			_, err := client.DeleteMessage(ctx, &sqs.DeleteMessageInput{
				QueueUrl:      aws.String(queueURL),
				ReceiptHandle: msg.ReceiptHandle,
			})
			if err != nil {
				log.Printf("failed to delete SQS message: %v", err)
			}
		}
	}
}

func strPtr(s string) *string {
	if s == "" {
		return nil
	}
	return &s
}
```

**Step 2: Verify it compiles**

Run: `go build ./...`
Expected: No errors.

**Step 3: Commit**

```bash
git add poller.go
git commit -m "feat: implement SQS poller"
```

---

### Task 4: Implement auth middleware

**Files:**
- Modify: `auth.go`

**Step 1: Implement cookie-based session auth**

```go
package main

import (
	"crypto/rand"
	"encoding/hex"
	"net/http"
	"sync"
	"time"
)

type sessionStore struct {
	mu       sync.RWMutex
	sessions map[string]time.Time
}

var sessions = &sessionStore{
	sessions: make(map[string]time.Time),
}

func (s *sessionStore) create() string {
	b := make([]byte, 32)
	rand.Read(b)
	token := hex.EncodeToString(b)

	s.mu.Lock()
	s.sessions[token] = time.Now().Add(24 * time.Hour)
	s.mu.Unlock()
	return token
}

func (s *sessionStore) valid(token string) bool {
	s.mu.RLock()
	expiry, ok := s.sessions[token]
	s.mu.RUnlock()
	if !ok {
		return false
	}
	if time.Now().After(expiry) {
		s.mu.Lock()
		delete(s.sessions, token)
		s.mu.Unlock()
		return false
	}
	return true
}

func (s *sessionStore) destroy(token string) {
	s.mu.Lock()
	delete(s.sessions, token)
	s.mu.Unlock()
}

func requireAuth(password string, next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		cookie, err := r.Cookie("session")
		if err != nil || !sessions.valid(cookie.Value) {
			http.Redirect(w, r, "/login", http.StatusSeeOther)
			return
		}
		next.ServeHTTP(w, r)
	})
}
```

**Step 2: Verify it compiles**

Run: `go build ./...`
Expected: No errors.

**Step 3: Commit**

```bash
git add auth.go
git commit -m "feat: implement session auth middleware"
```

---

### Task 5: Implement HTTP handlers and templates

**Files:**
- Modify: `handlers.go`
- Create: `templates/layout.html`
- Create: `templates/login.html`
- Create: `templates/messages.html`

**Step 1: Create `templates/layout.html`**

```html
{{define "layout"}}
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>mail-ingest</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: system-ui, sans-serif; max-width: 960px; margin: 0 auto; padding: 1rem; }
        h1 { margin-bottom: 1rem; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 0.5rem; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #f5f5f5; }
        a { color: #0066cc; }
        .verdict-pass { color: green; }
        .verdict-fail { color: red; }
        form { display: flex; flex-direction: column; gap: 0.5rem; max-width: 300px; }
        input, button { padding: 0.5rem; font-size: 1rem; }
        button { cursor: pointer; background: #0066cc; color: white; border: none; border-radius: 4px; }
        nav { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
        .pagination { display: flex; gap: 0.5rem; margin-top: 1rem; }
    </style>
</head>
<body>
    {{template "content" .}}
</body>
</html>
{{end}}
```

**Step 2: Create `templates/login.html`**

```html
{{define "content"}}
<h1>mail-ingest</h1>
<form method="POST" action="/login">
    <label for="password">Password</label>
    <input type="password" id="password" name="password" required autofocus>
    <button type="submit">Log in</button>
    {{if .Error}}<p style="color: red;">{{.Error}}</p>{{end}}
</form>
{{end}}
```

**Step 3: Create `templates/messages.html`**

```html
{{define "content"}}
<nav>
    <h1>mail-ingest ({{.Total}} messages)</h1>
    <form method="POST" action="/logout"><button type="submit">Log out</button></form>
</nav>
<table>
    <thead>
        <tr>
            <th>Date</th>
            <th>From</th>
            <th>Subject</th>
            <th>SPF</th>
            <th>DKIM</th>
            <th>DMARC</th>
            <th>Spam</th>
            <th>Raw</th>
        </tr>
    </thead>
    <tbody>
        {{range .Messages}}
        <tr>
            <td>{{.Timestamp}}</td>
            <td>{{.Source}}</td>
            <td>{{.Subject}}</td>
            <td class="{{verdictClass .SPFVerdict}}">{{deref .SPFVerdict}}</td>
            <td class="{{verdictClass .DKIMVerdict}}">{{deref .DKIMVerdict}}</td>
            <td class="{{verdictClass .DMARCVerdict}}">{{deref .DMARCVerdict}}</td>
            <td class="{{verdictClass .SpamVerdict}}">{{deref .SpamVerdict}}</td>
            <td>{{if .S3Key}}<a href="/message/{{.ID}}/raw">eml</a>{{end}}</td>
        </tr>
        {{else}}
        <tr><td colspan="8">No messages yet.</td></tr>
        {{end}}
    </tbody>
</table>
{{if gt .TotalPages 1}}
<div class="pagination">
    {{if gt .Page 1}}<a href="/?page={{prev .Page}}">prev</a>{{end}}
    <span>page {{.Page}} of {{.TotalPages}}</span>
    {{if lt .Page .TotalPages}}<a href="/?page={{next .Page}}">next</a>{{end}}
</div>
{{end}}
{{end}}
```

**Step 4: Implement `handlers.go`**

```go
package main

import (
	"context"
	"database/sql"
	"html/template"
	"log"
	"net/http"
	"strconv"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/service/s3"
)

const perPage = 50

var tmpl *template.Template

func init() {
	funcMap := template.FuncMap{
		"deref": func(s *string) string {
			if s == nil {
				return "-"
			}
			return *s
		},
		"verdictClass": func(s *string) string {
			if s == nil {
				return ""
			}
			if *s == "PASS" {
				return "verdict-pass"
			}
			return "verdict-fail"
		},
		"prev": func(i int) int { return i - 1 },
		"next": func(i int) int { return i + 1 },
	}
	tmpl = template.Must(template.New("").Funcs(funcMap).ParseGlob("templates/*.html"))
}

func newRouter(db *sql.DB, awsCfg aws.Config, cfg Config) http.Handler {
	mux := http.NewServeMux()

	mux.HandleFunc("GET /login", handleLoginPage)
	mux.HandleFunc("POST /login", handleLogin(cfg.AuthPassword))
	mux.HandleFunc("POST /logout", handleLogout)

	protected := http.NewServeMux()
	protected.HandleFunc("GET /", handleMessages(db))
	protected.HandleFunc("GET /message/{id}/raw", handleRawEmail(db, awsCfg, cfg.S3Bucket))

	mux.Handle("/", requireAuth(cfg.AuthPassword, protected))
	return mux
}

func handleLoginPage(w http.ResponseWriter, r *http.Request) {
	tmpl.ExecuteTemplate(w, "layout", struct{ Error string }{})
}

func handleLogin(password string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.FormValue("password") != password {
			tmpl.ExecuteTemplate(w, "layout", struct{ Error string }{"Invalid password."})
			return
		}
		token := sessions.create()
		http.SetCookie(w, &http.Cookie{
			Name:     "session",
			Value:    token,
			Path:     "/",
			HttpOnly: true,
			SameSite: http.SameSiteLaxMode,
			MaxAge:   86400,
		})
		http.Redirect(w, r, "/", http.StatusSeeOther)
	}
}

func handleLogout(w http.ResponseWriter, r *http.Request) {
	if cookie, err := r.Cookie("session"); err == nil {
		sessions.destroy(cookie.Value)
	}
	http.SetCookie(w, &http.Cookie{
		Name:   "session",
		Value:  "",
		Path:   "/",
		MaxAge: -1,
	})
	http.Redirect(w, r, "/login", http.StatusSeeOther)
}

func handleMessages(db *sql.DB) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		page, _ := strconv.Atoi(r.URL.Query().Get("page"))
		if page < 1 {
			page = 1
		}
		offset := (page - 1) * perPage

		messages, err := listMessages(db, perPage, offset)
		if err != nil {
			log.Printf("list messages error: %v", err)
			http.Error(w, "internal error", 500)
			return
		}

		total, err := countMessages(db)
		if err != nil {
			log.Printf("count messages error: %v", err)
			http.Error(w, "internal error", 500)
			return
		}

		totalPages := (total + perPage - 1) / perPage
		if totalPages < 1 {
			totalPages = 1
		}

		data := struct {
			Messages   []Message
			Total      int
			Page       int
			TotalPages int
		}{messages, total, page, totalPages}

		tmpl.ExecuteTemplate(w, "layout", data)
	}
}

func handleRawEmail(db *sql.DB, awsCfg aws.Config, bucket string) http.HandlerFunc {
	presigner := s3.NewPresignClient(s3.NewFromConfig(awsCfg))

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
		if msg == nil || msg.S3Key == nil {
			http.Error(w, "not found", 404)
			return
		}

		req, err := presigner.PresignGetObject(context.Background(), &s3.GetObjectInput{
			Bucket: aws.String(bucket),
			Key:    msg.S3Key,
		}, func(opts *s3.PresignOptions) {
			opts.Expires = 15 * time.Minute
		})
		if err != nil {
			log.Printf("presign error: %v", err)
			http.Error(w, "internal error", 500)
			return
		}

		http.Redirect(w, r, req.URL, http.StatusTemporaryRedirect)
	}
}
```

**Step 5: Verify it compiles**

Run: `go build ./...`
Expected: No errors.

**Step 6: Commit**

```bash
git add handlers.go auth.go templates/
git commit -m "feat: implement HTTP handlers and templates"
```

---

### Task 6: Wire everything together and test locally

**Step 1: Verify the full build**

Run: `go build -o mail-ingest .`
Expected: Produces a `mail-ingest` binary.

**Step 2: Test locally with a fake config**

Run:
```bash
AUTH_PASSWORD=test DB_PATH=./test.db SQS_QUEUE_URL=https://fake S3_BUCKET=fake ./mail-ingest
```

Expected: Server starts on `:8080`, SQS poller logs an error (expected -- no real queue). Visit `http://localhost:8080/login`, enter "test", see empty messages page.

**Step 3: Clean up test artifacts**

Run: `rm -f mail-ingest test.db`

**Step 4: Build Docker image locally**

Run: `docker build -t mail-ingest:test .`
Expected: Build succeeds.

**Step 5: Add `.gitignore`**

```
mail-ingest
*.db
```

**Step 6: Commit**

```bash
git add -A
git commit -m "feat: wire up main entry point, add gitignore and dockerfile"
```

---

### Task 7: Push and verify CI

**Step 1: Create GitHub repo**

Run: `gh repo create jackharrhy/mail-ingest --public --source=. --push`

**Step 2: Verify GitHub Actions builds and pushes image**

Run: `gh run watch`
Expected: Build succeeds, image pushed to `ghcr.io/jackharrhy/mail-ingest:main`.

**Step 3: Verify image exists**

Run: `docker pull ghcr.io/jackharrhy/mail-ingest:main`
Expected: Pull succeeds.

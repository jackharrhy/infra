package main

import (
	"context"
	"encoding/json"
	"log"
	"net"
	"net/http"
	"net/http/httputil"
	"os"
	"regexp"
	"strings"
	"time"
)

var ports = map[string]string{
	"atlas.pi.jackharrhy.dev":   "21981",
	"go-demo.pi.jackharrhy.dev": "21982",
}

const cookieName = "__Host-private-hosting"

const slidesHost = "slides.pi.jackharrhy.dev"

const worldHost = "world.pi.jackharrhy.dev"

func backendProxy(socket string) http.Handler {
	dialer := &net.Dialer{Timeout: 3 * time.Second}
	return &httputil.ReverseProxy{
		Transport: &http.Transport{DialContext: func(ctx context.Context, _, _ string) (net.Conn, error) {
			if socket == "" {
				return dialer.DialContext(ctx, "tcp", "127.0.0.1:21953")
			}
			return dialer.DialContext(ctx, "unix", socket)
		}, ResponseHeaderTimeout: 30 * time.Second},
		Rewrite: func(p *httputil.ProxyRequest) {
			p.Out.URL.Scheme = "http"
			p.Out.URL.Host = "private-hosting"
			p.Out.Host = p.In.Host
			upgrade := p.Out.Header.Get("Upgrade")
			p.Out.Header = make(http.Header)
			// ReverseProxy has already validated the Connection/Upgrade pairing.
			if (p.In.Host == slidesHost && p.In.URL.Path == "/position" || p.In.Host == worldHost && p.In.URL.Path == "/room") && p.In.Method == http.MethodGet && strings.EqualFold(upgrade, "websocket") {
				p.Out.Header.Set("Connection", "Upgrade")
				p.Out.Header.Set("Upgrade", "websocket")
				for _, key := range []string{"Sec-WebSocket-Key", "Sec-WebSocket-Version", "Sec-WebSocket-Protocol", "Sec-WebSocket-Extensions"} {
					if values := p.In.Header.Values(key); len(values) > 0 {
						p.Out.Header[http.CanonicalHeaderKey(key)] = values
					}
				}
			}
			for _, key := range []string{"Accept", "Accept-Encoding", "Accept-Language", "Content-Type", "Content-Encoding", "Origin", "Referer", "Range", "If-Range", "If-None-Match", "If-Modified-Since", "Cache-Control", "User-Agent", "Sec-Fetch-Site", "Sec-Fetch-Mode", "Sec-Fetch-Dest"} {
				if v := p.In.Header.Values(key); len(v) > 0 {
					p.Out.Header[key] = v
				}
			}
			if p.In.Host == slidesHost {
				for _, c := range p.In.Cookies() {
					if slidesCookie(c.Name) {
						p.Out.AddCookie(c)
					}
				}
			}
			p.Out.Header.Set("X-Forwarded-Proto", "https")
			if p.In.Host == slidesHost {
				p.Out.Header.Set("X-Forwarded-Host", slidesHost)
			}
		},
		ModifyResponse: func(r *http.Response) error {
			r.Header.Set("Cache-Control", "private, no-store")
			cookies := r.Cookies()
			r.Header.Del("Set-Cookie")
			if r.Request.Host == slidesHost {
				for _, c := range cookies {
					if slidesCookie(c.Name) && c.Secure && c.HttpOnly && c.Path == "/" && c.Domain == "" {
						r.Header.Add("Set-Cookie", c.String())
					}
				}
			}
			return nil
		},
	}
}

func slidesGateway(socket string) http.Handler {
	app := backendProxy(socket)
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Cache-Control", "private, no-store")
		if r.Host != slidesHost || r.URL.IsAbs() || r.URL.EscapedPath() != r.URL.Path {
			http.NotFound(w, r)
			return
		}
		var allowed bool
		switch r.URL.Path {
		case "/", "/allo.woff2", "/demo-night.jpg":
			allowed = r.Method == "GET" || r.Method == "HEAD"
		case "/position":
			allowed = r.Method == "GET" || r.Method == "POST"
		case "/auth/login", "/auth/callback":
			allowed = r.Method == "GET"
		case "/auth/logout":
			allowed = r.Method == "POST"
		}
		if !allowed {
			http.NotFound(w, r)
			return
		}
		app.ServeHTTP(w, r)
	})
}

func gateway(owner, socket string) http.Handler {
	return ownerGate(owner, ports, backendProxy(socket))
}

func ownerGate(owner string, ports map[string]string, app http.Handler) http.Handler {
	oauthTransport := &http.Transport{ResponseHeaderTimeout: 10 * time.Second}
	auth := &http.Client{Transport: oauthTransport, Timeout: 3 * time.Second, CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse }}
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Cache-Control", "private, no-store")
		port, ok := ports[r.Host]
		if !ok {
			http.NotFound(w, r)
			return
		}
		if r.URL.IsAbs() || !strings.HasPrefix(r.URL.Path, "/") {
			http.Error(w, "Bad request", 400)
			return
		}
		base := "http://127.0.0.1:" + port
		if r.URL.Path == "/oauth2/start" || r.URL.Path == "/oauth2/callback" {
			if r.Method != "GET" || r.URL.EscapedPath() != r.URL.Path {
				http.NotFound(w, r)
				return
			}
			p := &httputil.ReverseProxy{Transport: oauthTransport, Rewrite: func(p *httputil.ProxyRequest) {
				p.Out.URL.Scheme = "http"
				p.Out.URL.Host = "127.0.0.1:" + port
				p.Out.Host = r.Host
				p.Out.Header = make(http.Header)
				p.Out.Header.Set("Cookie", oauthCookies(r))
				if r.URL.Path == "/oauth2/start" {
					p.Out.URL.RawQuery = "rd=%2F"
				}
			}}
			p.ServeHTTP(w, r)
			return
		}
		if strings.HasPrefix(r.URL.Path, "/oauth2/") {
			http.NotFound(w, r)
			return
		}
		q, err := http.NewRequestWithContext(r.Context(), "GET", base+"/oauth2/auth", nil)
		if err != nil {
			http.Error(w, "Auth unavailable", 503)
			return
		}
		q.Host = r.Host
		q.Header.Set("Cookie", oauthCookies(r))
		reply, err := auth.Do(q)
		if err != nil {
			http.Error(w, "Auth unavailable", 503)
			return
		}
		reply.Body.Close()
		switch reply.StatusCode {
		case http.StatusAccepted:
			sub := reply.Header.Values("X-Auth-Request-User")
			if len(sub) != 1 || sub[0] != owner {
				http.Error(w, "Forbidden", 403)
				return
			}
			app.ServeHTTP(w, r)
		case http.StatusUnauthorized:
			if (r.Method == "GET" || r.Method == "HEAD") && strings.Contains(r.Header.Get("Accept"), "text/html") {
				http.Redirect(w, r, "/oauth2/start", 302)
				return
			}
			http.Error(w, "Sign-in required", 401)
		case http.StatusForbidden:
			http.Error(w, "Forbidden", 403)
		default:
			http.Error(w, "Auth unavailable", 503)
		}
	})
}

func slidesCookie(name string) bool {
	return name == "__Host-slides_session" || strings.HasPrefix(name, "__Host-slides_oauth_") || strings.HasPrefix(name, "__Host-slides_enrollment_")
}

func oauthCookies(r *http.Request) string {
	var values []string
	for _, c := range r.Cookies() {
		if c.Name == cookieName || strings.HasPrefix(c.Name, cookieName+"_") {
			values = append(values, c.String())
		}
	}
	return strings.Join(values, "; ")
}

func main() {
	if len(os.Args) == 3 && os.Args[1] == "--slides" && strings.HasPrefix(os.Args[2], "/") {
		serve("127.0.0.1:21984", slidesGateway(os.Args[2]))
		return
	}
	if len(os.Args) != 3 {
		log.Fatal("usage: gateway provider.json caddy.sock")
	}
	raw, err := os.ReadFile(os.Args[1])
	if err != nil {
		log.Fatal("cannot read provider config")
	}
	var config struct{ Account string }
	if json.Unmarshal(raw, &config) != nil || strings.TrimSpace(config.Account) == "" || strings.ContainsAny(config.Account, ",\r\n") {
		log.Fatal("invalid owner binding")
	}
	if os.Args[2] == "--world" {
		serve("127.0.0.1:21985", ownerGate(config.Account, map[string]string{worldHost: "21986"}, worldApp()))
		return
	}
	// A reverse proxy must not resolve any client-selected authority.
	if !strings.HasPrefix(os.Args[2], "/") {
		log.Fatal("expected absolute Caddy socket path")
	}
	serve("127.0.0.1:21980", gateway(config.Account, os.Args[2]))
}

func serve(addr string, handler http.Handler) {
	s := &http.Server{Addr: addr, Handler: handler, ReadHeaderTimeout: 5 * time.Second, IdleTimeout: 60 * time.Second, MaxHeaderBytes: 65536}
	log.Fatal(s.ListenAndServe())
}

var worldAsset = regexp.MustCompile(`^/(assets|textures|billboard|audio)/[a-zA-Z0-9._-]+$`)

func worldApp() http.Handler {
	app := backendProxy("")
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet && r.Method != http.MethodHead || r.URL.EscapedPath() != r.URL.Path {
			http.NotFound(w, r)
			return
		}
		switch r.URL.Path {
		case "/", "/healthz", "/maps/hall.bsp", "/world.css":
		case "/room":
			if r.Method != http.MethodGet || r.Header.Get("Origin") != "https://"+worldHost {
				http.Error(w, "Forbidden", 403)
				return
			}
		default:
			if !worldAsset.MatchString(r.URL.Path) || strings.HasSuffix(r.URL.Path, "/.") || strings.HasSuffix(r.URL.Path, "/..") {
				http.NotFound(w, r)
				return
			}
		}
		app.ServeHTTP(w, r)
	})
}

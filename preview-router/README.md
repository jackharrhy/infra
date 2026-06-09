# Newport preview router

Local-dev preview router for running multiple project previews on `newport`.

## URLs

Preferred no-port URLs, routed by Traefik on `:80` with tailnet-only `ipAllowList`:

- http://{project-name}.newport/ - hit traefik, redirect to caddy
- http://preview.newport:18088/ - hit caddy directly, route to project
- https://newport.hedgehog-python.ts.net:844{project-port} - hit over tailscale https urls

```bash
uv run preview-router start
uv run preview-router status
uv run preview-router stop
```

Each target repo owns its own local config file:

```text
.preview-router.toml
```

Example config:

```toml
name = "Example App"
hostnames = ["example.newport"]
app_host = "example.localhost"
app_port = 5555
caddy_port = 18086
tailscale_port = 8446
command = "pnpm run dev"
readiness_path = "/"
readiness_statuses = [200, 302]

[env]
SOME_ENV = "value"
```

## Architecture

```text
Browser on tailnet -> Traefik :80 -> host Caddy :18088 -> app dev server on 127.0.0.1
Tailscale Serve HTTPS high port -> host Caddy per-service port -> app dev server on 127.0.0.1
```

Traefik config lives in `./hosts/newport/traefik/dynamic/preview-router.yml`
```

Traefik runs in host-network mode so it can reach the host-local Caddy preview stack directly. The dynamic route is protected with an `ipAllowList` for Tailscale/localhost only. The Caddy listeners, preview UI, app dev servers, and dev databases should all bind to `127.0.0.1`.

```text
Host router
  127.0.0.1:18088 -> Project by Host header

Tailscale Serve HTTPS ports
  844{project port} -> 127.0.0.1:1808{project port} -> Project dev server
```

## `/etc/hosts` helper

Generate a local installer script from the configured project hostnames when the `*.newport` names do not resolve on a device:

```bash
uv run preview-router hosts-script --output install-hosts.sh
# or print it without writing a file:
uv run preview-router hosts-script --output -
```

`install-hosts.sh` is generated local state and is intentionally gitignored. The generated script manages a block like:

```text
100.x.y.z preview.newport {project 1}.newport {project 2}.newport {project n}.newport
```

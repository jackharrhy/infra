# Preview router

Python/uv local-dev preview router for running multiple project previews behind one localhost-bound Caddy router, optional Traefik host routing, and optional Tailscale Serve HTTPS ports.

The repo is intentionally generic. Host-specific values live in a local `preview-router.toml`, and project wiring lives in ignored `projects/` symlinks plus each target repo's `.preview-router.toml`.

## Configure this host

```bash
cp preview-router.example.toml preview-router.toml
$EDITOR preview-router.toml
```

Root config fields are top-level TOML keys:

```toml
preview_hostname = "preview.example.test"
host_domain = "example.test"
tailscale_host = ""
host_router_port = 18088
ui_port = 18089
caddy_container = "preview-caddy"
caddy_admin_listen = "127.0.0.1:2019"
projects_dir = "projects"
```

- `preview_hostname`: hostname for the status UI.
- `host_domain`: optional suffix for project hostnames when a project does not set `hostnames`.
- `tailscale_host`: optional MagicDNS/FQDN used only to print Tailscale HTTPS URLs.
- `host_router_port`: localhost-bound Caddy Host-header router port.
- `ui_port`: localhost-bound status UI port.
- `projects_dir`: directory of symlinks to repos.

## Add projects

Create ignored symlinks under `projects_dir`:

```bash
mkdir -p projects
ln -sfn /path/to/app projects/app
```

Each target repo owns its own local config file:

```text
.preview-router.toml
```

Example project config:

```toml
name = "Example App"
hostnames = ["app.example.test"]
app_host = "app.localhost"
app_port = 5555
caddy_port = 18086
tailscale_port = 8446
command = "pnpm run dev"
readiness_path = "/"
readiness_statuses = [200, 302]

[env]
SOME_ENV = "value"
```

If `hostnames` is omitted, the router uses `{project-symlink-name}.{host_domain}`. If `caddy_port` and `tailscale_port` are set, `preview-router start` also configures `tailscale serve` for that project.

## Run

```bash
uv run preview-router start
uv run preview-router status
uv run preview-router stop
```

## Architecture

```text
Browser on trusted network -> optional external proxy :80 -> host Caddy host_router_port -> app dev server on 127.0.0.1
Tailscale Serve HTTPS high port -> host Caddy per-service caddy_port -> app dev server on 127.0.0.1
```

Keep the generated Caddy listeners, preview UI, app dev servers, and dev databases bound to `127.0.0.1`. If you front this with Traefik/Caddy/nginx on a LAN-facing port, protect that route with a tailnet/VPN-only allowlist.

## `/etc/hosts` helper

Generate a local installer script from the configured project hostnames when the names do not resolve on a device:

```bash
uv run preview-router hosts-script --output install-hosts.sh
# or print it without writing a file:
uv run preview-router hosts-script --output -
```

`install-hosts.sh` is generated local state and is intentionally gitignored. The generated script manages a block like:

```text
100.x.y.z preview.example.test app.example.test another-app.example.test
```

Override the generated IP if needed:

```bash
uv run preview-router hosts-script --preview-ip 100.x.y.z --output install-hosts.sh
```

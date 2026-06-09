# Preview router

Local preview router for a pile of dev servers. It uses Python/uv, Caddy, optional Traefik host routing, and optional Tailscale Serve ports.

The checked-in code is generic. Put host-specific values in local `preview-router.toml`. Put project wiring in ignored `projects/` symlinks and each repo's `.preview-router.toml`.

## Host config

```bash
cp preview-router.example.toml preview-router.toml
$EDITOR preview-router.toml
```

Example:

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

Notes:

- `preview_hostname`: status UI hostname
- `host_domain`: suffix for project hostnames when a project does not set `hostnames`
- `tailscale_host`: MagicDNS/FQDN used when printing HTTPS URLs
- `host_router_port`: localhost Caddy Host-header router
- `ui_port`: localhost status UI
- `projects_dir`: symlinks to repos

## Projects

Add ignored symlinks:

```bash
mkdir -p projects
ln -sfn /path/to/app projects/app
```

Each target repo can have a local `.preview-router.toml`:

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

If `hostnames` is missing, the router uses `{project-symlink-name}.{host_domain}`. If `caddy_port` and `tailscale_port` are set, `start` also configures `tailscale serve` for that project.

## Run

```bash
uv run preview-router start
uv run preview-router status
uv run preview-router stop
```

## Shape

```text
trusted browser -> optional external proxy :80 -> Caddy host_router_port -> app on 127.0.0.1
Tailscale Serve HTTPS port -> Caddy caddy_port -> app on 127.0.0.1
```

Keep Caddy listeners, the UI, dev servers, and dev databases on `127.0.0.1`. If a LAN-facing proxy sits in front, lock it down to your tailnet/VPN.

## Hosts helper

Generate a local `/etc/hosts` installer when a device cannot resolve your preview names:

```bash
uv run preview-router hosts-script --output install-hosts.sh
uv run preview-router hosts-script --output -
```

`install-hosts.sh` is generated local state and is gitignored. It manages a block like this:

```text
100.x.y.z preview.example.test app.example.test another-app.example.test
```

Override the IP if needed:

```bash
uv run preview-router hosts-script --preview-ip 100.x.y.z --output install-hosts.sh
```

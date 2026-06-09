# Newport preview router

Python/uv local-dev preview router for running multiple project previews on `newport`.

The router lives in this public infra repo at `~/infra/preview-router`, but project wiring is local-only: `projects/`, `.run/`, `logs/`, generated Caddy config, and virtualenvs are gitignored. Do not commit secrets here; use the repo's existing SOPS patterns if a future shared secret is genuinely required.

## URLs

Preferred no-port URLs, routed by Traefik on `:80` with tailnet-only `ipAllowList`:

```text
Preview UI       http://preview.newport/
DwellSmart       http://dwellsmart.newport/
Silicon Harbour  http://siliconharbour.newport/  or http://silicon.newport/
where-the-plow   http://plow.newport/            or http://where-the-plow.newport/
```

Caddy host-router fallback URLs, bound to localhost on the host:

```text
Preview UI       http://preview.newport:18088/
DwellSmart       http://dwellsmart.newport:18088/
Silicon Harbour  http://siliconharbour.newport:18088/
where-the-plow   http://plow.newport:18088/
```

Tailnet HTTPS URLs for direct Tailscale Serve access:

```text
DwellSmart       https://newport.hedgehog-python.ts.net:8443/
Silicon Harbour  https://newport.hedgehog-python.ts.net:8444/
where-the-plow   https://newport.hedgehog-python.ts.net:8445/
```

## Start / stop / status

```bash
cd ~/infra/preview-router
uv run preview-router start
uv run preview-router status
uv run preview-router stop --legacy
```

`--legacy` also kills old one-off Portless/shell-script processes from earlier iterations.

## Local project wiring

Projects are local symlinks under ignored `projects/`:

```text
projects/dwellsmart        -> ~/repos/personal/dwellsmart
projects/siliconharbour    -> ~/repos/personal/siliconharbour.dev
projects/where-the-plow    -> ~/repos/personal/where-the-plow
```

Create/repair them on `newport` with:

```bash
cd ~/infra/preview-router
mkdir -p projects
ln -sfn ~/repos/personal/dwellsmart projects/dwellsmart
ln -sfn ~/repos/personal/siliconharbour.dev projects/siliconharbour
ln -sfn ~/repos/personal/where-the-plow projects/where-the-plow
```

Each target repo owns its own local config file:

```text
.preview-router.toml
```

That filename is added to the global git excludes file (`~/.config/git/ignore`) so project-specific preview details do not need to be committed to the individual repos or copied into this public infra repo.

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

Traefik config lives in:

```text
~/infra/hosts/newport/traefik/dynamic/preview-router.yml
```

Traefik runs in host-network mode so it can reach the host-local Caddy preview stack directly. The dynamic route is protected with an `ipAllowList` for Tailscale/localhost only. The Caddy listeners, preview UI, app dev servers, and dev databases should all bind to `127.0.0.1`.

```text
Host router
  127.0.0.1:18088 -> DwellSmart/Silicon Harbour/where-the-plow/Preview UI by Host header

Tailscale Serve HTTPS ports
  8443 -> 127.0.0.1:18083 -> DwellSmart dev server
  8444 -> 127.0.0.1:18084 -> Silicon Harbour dev server
  8445 -> 127.0.0.1:18085 -> where-the-plow dev server
```

Runtime files live under ignored directories:

```text
.run/   pid files + generated caddy.json
logs/   process logs
```

## MacBook `/etc/hosts` helper

Copy and run `install-mac-hosts.sh` on the MacBook if the `*.newport` names do not resolve there.

It manages this block:

```text
100.123.66.70 dwellsmart.newport siliconharbour.newport silicon.newport plow.newport where-the-plow.newport preview.newport
```

`/etc/hosts` maps names to IPs only. For custom `*.newport` names, use HTTP. Tailscale HTTPS certificates are for `newport.hedgehog-python.ts.net`, not `*.newport`.

## Inspection

```bash
cd ~/infra/preview-router
uv run preview-router status
tailscale serve status --json
docker ps --format '{{.Names}} {{.Status}} {{.Ports}}' | grep -E 'preview-caddy|newport-traefik'
curl -H 'Host: dwellsmart.newport' http://127.0.0.1/
curl -H 'Host: preview.newport' http://127.0.0.1/
```

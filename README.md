# infra

my infra

diagram: https://jackharrhy.github.io/infra/infra.svg

![Infrastructure diagram](https://jackharrhy.github.io/infra/infra.svg)

- `.github/workflows/pages.yml`: deploys `docs/` to GitHub Pages
- `aws/`: Pulumi bits
- `dns/`: octoDNS config and zone files
- `docs/`: generated D2/SVG diagram and old planning notes
- `hosts/mug/`: DigitalOcean host compose stack
- `hosts/newport/`: home host compose stack
- `hosts/newport/cheesetown/`: cheesetown Minecraft stack
- `scripts/`: small helper scripts
- `cli.py`: the `infra` CLI
- `infra.yml`: host metadata and diagram hints

## CLI

Install the shortcut:

```bash
uv run cli.py install
```

Or run it directly:

```bash
uv run cli.py --help
```

Useful commands:

```bash
infra status
infra status newport
infra update newport
infra refresh newport
infra diagram
infra diagram --format png
infra diagram --no-render
```

`infra diagram` reads the compose files plus `infra.yml`, writes `docs/infra.d2`, and renders `docs/infra.svg` if `d2` is installed.

## Secrets

Secrets are SOPS-encrypted YAML files. Rendered `.env` files go under sibling `.runtime-secrets/` directories.

```bash
sops hosts/{host}/secrets/{service}.enc.yaml
./scripts/render-secrets.sh newport
```

## DNS

DNS is managed with octoDNS and DigitalOcean.

```bash
infra dns dump
infra dns diff
infra dns diff jackharrhy.com.
infra dns sync
infra dns sync jackharrhy.com.
```

`sync` shows the plan first and asks before applying.

## NAS

NAS commands use `nas/secrets/synology.enc.yaml`.

```bash
infra nas login-check
infra nas shares
infra nas debug-share SHARE
infra nas nfs list SHARE
infra nas nfs grant SHARE CLIENT_PATTERN
infra nas nfs revoke SHARE CLIENT_PATTERN --yes
```

## Minecraft

cheesetown lives in its own Compose project:

On a fresh host, provision `.runtime-secrets/rcon-password` inside that directory
with a random password and mode `600` before starting Compose.

```bash
cd hosts/newport/cheesetown
docker compose up -d --wait --wait-timeout 180
```

See the [optional client pack](hosts/newport/cheesetown/client-pack/README.md).
Persistent data is under `/mnt/terrabud/docker-data/newport/cheesetown/`; retired server data
is under `/mnt/terrabud/docker-data/newport/retired-minecraft/`, outside infra.

## Remote hosts

SSH targets and compose paths live in `infra.yml`.

```bash
infra status
infra update mug
infra refresh mug
```

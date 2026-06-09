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
- `hosts/newport/minecraft/`: Minecraft stack and backups
- `preview-router/`: local multi-project preview router
- `scripts/`: small helper scripts
- `cli.py`: the `infra` CLI
- `infra.yml`: host metadata and diagram hints

## CLI

Install the shortcut:

```bash
uv run --script cli.py install
```

Or run it directly:

```bash
uv run --script cli.py --help
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

## Preview router

`preview-router/` runs local project previews behind a small Caddy router. Host-specific config lives in ignored local files.

```bash
cd preview-router
cp preview-router.example.toml preview-router.toml
uv run preview-router start
uv run preview-router status
uv run preview-router hosts-script --output install-hosts.sh
uv run preview-router stop
```

See `preview-router/README.md` for the full setup.

## Minecraft

Minecraft lives in its own compose project:

```bash
cd hosts/newport/minecraft
../../../scripts/render-secrets.sh newport
docker compose pull
docker compose up -d
```

Runtime data and backups stay out of git:

- `hosts/newport/minecraft/data/`
- `hosts/newport/minecraft/backups/`

## Remote hosts

SSH targets and compose paths live in `infra.yml`.

```bash
infra status
infra update mug
infra refresh mug
```

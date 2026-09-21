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

```bash
uv run cli.py install
```

```bash
infra status
infra status newport
infra update newport
infra refresh newport
infra refresh mug --service radio-celld
infra diagram
infra diagram --format png
infra diagram --no-render
```

`infra diagram` reads the compose files plus `infra.yml`, writes `docs/infra.d2`, and renders `docs/infra.svg` if `d2` is installed.

Use repeatable `refresh HOST --service NAME` options for a scoped application rollout. This
pulls and starts only the named services without starting dependencies or pruning rollback
images. A full-host refresh retains its existing image-pruning behavior. Storage-format
upgrades still require stopping writers and taking a consistent backup before refresh.

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

cheesetown lives in its own Compose project

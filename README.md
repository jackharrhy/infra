# infra

my infra

![Infrastructure diagram](https://jackharrhy.github.io/infra/infra.svg)

- `hosts/`: Compose stacks and service-specific storage/rollback notes
- `dns/`: octoDNS zones and configuration
- `aws/`: Pulumi resources and mail setup
- `scripts/`: volume setup, secret rendering, and import tools
- `cli.py`, `infra.yml`: fleet commands and diagram inputs
- `docs/`: generated diagram, published by GitHub Pages

## CLI

```sh
uv run cli.py install
infra status newport
infra update newport
infra refresh mug --service radio-celld
infra diagram
```

`status` compares Git revisions, not service health. `update` pulls Git only.
Use repeated `--service NAME` options to refresh selected services without
starting dependencies or pruning images. A full-host `refresh` also prunes
unused images.

`diagram` writes `docs/infra.d2` and renders SVG with `d2`. Use `--no-render`
for source only, or `--format png` for PNG.

## Secrets and DNS

Secrets are SOPS-encrypted YAML. Rendered files go into sibling
`.runtime-secrets/` directories and stay out of Git.

```sh
sops hosts/{host}/secrets/{service}.enc.yaml
./scripts/render-secrets.sh newport
infra dns dump
infra dns diff jackharrhy.com.
infra dns sync jackharrhy.com.
```

DNS uses DigitalOcean. `sync` shows the plan and asks before applying.
Mail setup and outstanding DKIM work are in [aws/README.md](aws/README.md).

## NAS

Credentials: `nas/secrets/synology.enc.yaml`.

```sh
infra nas login-check
infra nas shares
infra nas debug-share SHARE
infra nas nfs list SHARE
infra nas nfs grant SHARE CLIENT_PATTERN
infra nas nfs revoke SHARE CLIENT_PATTERN --yes
```

Cheesetown has its own Compose project under `hosts/newport/cheesetown/`.

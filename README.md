# infra

![Infrastructure diagram](https://jackharrhy.github.io/infra/infra.svg)

- `hosts/`: Compose stacks and service-specific operating notes
- `dns/`: octoDNS zones and configuration
- `aws/`: Pulumi resources and mail setup
- `docs/`: generated diagram, published by GitHub Pages
- [`maintenance/github-actions/`](maintenance/github-actions/): standalone CI recipes
  and the process for maintaining application workflows without central dependencies

## CLI

```sh
uv run cli.py install
infra status newport
infra update newport
infra refresh mug --service radio-celld
infra diagram
```

`status` compares Git revisions, not service health. `update` pulls Git only.
Repeated `--service NAME` options refresh selected services without starting
dependencies or pruning images. An unscoped `refresh HOST` refreshes the whole
host stack and prunes all unused images. Nested projects such as Cheesetown are
separate (`hosts/newport/cheesetown/`).

`diagram` writes `docs/infra.d2` and renders with `d2`; `--no-render` writes source only.

## Secrets and DNS

Secrets are SOPS-encrypted YAML; rendering requires `sops` and an age key.
Rendered `.runtime-secrets/` files stay out of Git.

```sh
sops hosts/{host}/secrets/{service}.enc.yaml
./scripts/render-secrets.sh newport
infra dns diff jackharrhy.com.
infra dns sync jackharrhy.com.
```

DNS uses DigitalOcean. `sync` asks before applying; `infra dns dump` pulls records.
Mail setup is in [aws/README.md](aws/README.md).

## NAS

Credentials: `nas/secrets/synology.enc.yaml`.

```sh
infra nas login-check
infra nas shares
infra nas search 'whitelist.json' --name-only
infra nas search minecraft --limit 50 --offset 0 --json
infra nas nfs list SHARE
infra nas nfs grant SHARE CLIENT_PATTERN
infra nas nfs revoke SHARE CLIENT_PATTERN --yes
```

Search uses DSM's index and account permissions, not a local crawl. Returned NAS
paths are not local mount paths. See `infra nas search --help` for options.

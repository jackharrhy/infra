# infra

https://jackharrhy.github.io/infra/infra.svg

![Infrastructure diagram of all of my services](https://jackharrhy.github.io/infra/infra.svg)

## Secrets

Secrets are stored as SOPS-encrypted YAML files and rendered into local `.env` files under `.runtime-secrets/`.

Requirements:
- `sops` installed
- age key available to `sops`

Edit a secret in place:

```bash
sops hosts/{dir}/secrets/{service}.enc.yaml
```

Render all secrets for a host:

```bash
./scripts/render-secrets.sh newport
```

That command renders every matching secret under `hosts/newport/**/secrets/` into a sibling `.runtime-secrets/` directory.

## CLI

Install the `infra` shortcut:

```bash
uv run --script cli.py install
```

Commands:

```bash
infra status
infra status newport
infra update newport
infra refresh newport
infra diagram
infra diagram --format png
```

DNS commands:

```bash
infra dns dump
infra dns diff
infra dns sync
```

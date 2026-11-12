# infra

Compose stacks, routing, DNS and operational tooling for Mug and Newport.

- [Operations](docs/operations.md): scoped maintenance, updates, routing, SOPS, DNS and NAS.
- [Applications](docs/applications.md): Auth, sites, publishing and application recovery.
- [Media](docs/media.md): playback, requests, acquisition and protected administration.
- [Games](docs/games.md): Cheesetown, Sven Co-op and world/asset backups.
- [AWS](aws/README.md): infrastructure and mail configuration.
- [Application CI guidance](maintenance/github-actions/README.md).

`hosts/` contains deployment configuration and helpers; current operating notes live
in `docs/`, not beside each service. Application repositories own application development
instructions. `dns/` contains octoDNS configuration; `aws/` contains Pulumi resources.

From `~/infra`:

```sh
uv run cli.py install
infra status newport
infra refresh mug --service radio-celld
```

`status` compares Git revisions, not health. Refresh only explicitly selected
services; an unscoped refresh also prunes unused images. Read the operations
policy before deployment. Nested game projects are separate Compose stacks.

![Infrastructure diagram](https://jackharrhy.github.io/infra/infra.svg)

`infra diagram` regenerates the diagram in `docs/` (`--no-render` writes D2 only).

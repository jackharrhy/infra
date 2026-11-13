# infra

Compose stacks, routing, DNS and operational tooling for Mug and Newport.

- [Operations](docs/operations.md): scoped maintenance, updates, routing, SOPS, DNS and NAS.
- [Host maintenance](docs/host-maintenance.md): storage, packages, kernels and remote access.
- [Applications](docs/applications.md): Auth, sites, publishing and application recovery.
- [Media](docs/media.md): playback, requests, acquisition and protected administration.
- [Games](docs/games.md): Cheesetown, Sven Co-op and world/asset backups.
- [AWS](aws/README.md): infrastructure and mail configuration.
- [Application CI guidance](maintenance/github-actions/README.md).
- [Agent operation](docs/agent-operations.md): shared knowledge and explicit ownership transfer.

`hosts/` contains deployment configuration and helpers; current operating notes live
in `docs/`, not beside each service. Application repositories own application development
instructions. `dns/` contains octoDNS configuration; `aws/` contains Pulumi resources.

Repository-owned agent skills live in [`.agents/skills`](.agents/skills):

- [Fleet operations](.agents/skills/infra-host-maintenance/SKILL.md).
- [Host/system maintenance](.agents/skills/host-system-maintenance/SKILL.md).
- [Applications and media](.agents/skills/infra-services/SKILL.md).
- [Games](.agents/skills/infra-games/SKILL.md).

They use the same CLI and guides as a human operator; private chat history is not
required. Current approvals, holds and responsibility decisions stay in the
operator's private handoff, not public standing instructions.

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

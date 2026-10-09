# Newport Shell

`newport-shell.service` listens on `127.0.0.1:8796`. The two active Traefik
`dynamic/newport-shell.yml` files expose only the exact MCP and metadata paths.
The `.staged` routers are templates, not watched configuration.

Root-owned helper and quota setup lives in the Newport Shell application's
`deploy/` directory. Its `RUNBOOK.md` covers installation, limits, and rollback.
Execution uses separate `newport-control` and `newport-exec` accounts; the latter
must not gain sudo or Docker access.

`control.env.example` keeps execution disabled. The installed production env
and introspection credential stay private under `/etc/newport-shell/`; do not
commit `control.env.production` or copy live credentials into the example.

The provider is 4orm at `https://4orm.harrhy.xyz`. Keep its locally built image
pinned until the combined OAuth changes are published. Hosted-client OAuth
compatibility still needs an end-to-end test.

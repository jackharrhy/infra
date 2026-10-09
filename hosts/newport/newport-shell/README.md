# Newport Shell

`newport-shell.service` listens on `127.0.0.1:8796`. Both hosts' Traefik
`dynamic/newport-shell.yml` files route the MCP and metadata paths.

The application's `deploy/` directory contains the root-owned helper and quota
setup. Execution uses separate `newport-control` and `newport-exec` accounts;
`newport-exec` has no sudo or Docker access.

Production env and introspection credentials live under `/etc/newport-shell/`.
`control.env.example` disables execution. OAuth uses `https://4orm.harrhy.xyz`.

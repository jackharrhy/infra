# slskd setup

Open https://slskd.rotund.org and sign in through `auth.jackharrhy.dev` using
the existing owner-only media-admin grant. Native UI authentication remains a
second gate; its username is `owner`. Retrieve the password in your private terminal:

```sh
cd ~/infra
sops --decrypt --extract '["SLSKD_PASSWORD"]' hosts/newport/secrets/slskd.enc.yaml
```

Do not paste the password into chat. Native UI authentication is separate from a
Soulseek account. Preserve the encrypted input and `/mnt/terrabud/docker-data/newport/slskd`
together for recovery; stop the service before restoring its state into an empty
destination.

## Disconnected commissioning boundary

The service deliberately starts with `no_connect`, no automatic share scan and an
internal-only Docker network without a default route or published ports. Host-network
Traefik reaches its fixed internal bridge address. Public DNS/TLS ingress is Mug,
relaying to Newport's `web` router behind the dedicated `slskd-auth` OAuth2 proxy,
using the same owner subject allowlist and issuer project as the other media-admin
services. API and WebSocket paths use that gate too; no Tailnet router bypasses it.
The proxy has its own client and host-only secure cookie, separate from native UI
credentials. Do not attach slskd itself to `web` merely to fix connectivity.
Watchtower remains enabled; replacements retain the isolated network and mounts.

Only canonical `library/music` is mounted read-only as `/music`. Only
`downloads/soulseek` is mounted writable for incomplete/complete downloads. State,
secrets and downloads are not shared. Remote configuration/file management remain
disabled. No Soulseek credentials are provisioned and transfers must remain empty.

Before enabling P2P, tell the owner that peers will see the Soulseek username,
public connection IP and shared music filenames and can request uploads consuming
bandwidth. Agree concrete upload limits and any incoming-port exposure; no incoming
P2P port is currently published. Have the owner enter the separate account securely
using SOPS (`SLSKD_SLSK_USERNAME` and `SLSKD_SLSK_PASSWORD`, verifying the installed
version's names first), not chat. Then explicitly authorize the egress/config
cutover, scan and verify the music-only share before any downloads. Enabling egress
requires a deliberate network change as well as removing `no_connect`; UI login
alone cannot bypass isolation.

Operate only this service with scoped Compose commands. No sibling recreation or
Docker pruning is required. Validate authenticated state and empty transfer queues,
public TLS, anonymous SSO redirection/API denial and the internal network after
maintenance. A real owner browser SSO session is a separate acceptance check from
native login or a redirect probe.

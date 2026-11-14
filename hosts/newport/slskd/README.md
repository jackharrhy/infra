# slskd private setup

Open https://slskd.rotund.org while connected to Tailscale. Native UI
username is `owner`. Retrieve the unique password in your own private terminal:

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
Traefik reaches its fixed internal bridge address; only the explicit `pitailnet`
router serves it. The explicit Tailnet A record suppresses the public wildcard
(including AAAA). DNS-01 TLS uses `newportdns`; octoDNS excludes only this host's
transient ACME challenge record from reconciliation. Do not attach the service to `web` merely to fix connectivity.
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
private TLS, public-listener denial and the internal network after maintenance.

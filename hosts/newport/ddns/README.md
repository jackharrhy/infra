# Newport dynamic DNS

`ddns.timer` runs octoDNS from Newport two minutes after boot and every five
minutes thereafter (up to 30 seconds of jitter). Records have a 300-second TTL.
A failed lookup or provider request fails the service and retries next tick;
the service has a 90-second timeout. No separate DNS writer or cached IP file.

Current names:

- `craft.jackharrhy.dev`
- `cheesetown.rocks` (zone apex)

`dns/config.yaml` combines each zone's static YAML source with the native
`octodns_ddns.DdnsSource`. That package uses its provider ID as the record name:
`craft` for the subdomain, `''` for an apex. The IPv4 lookup uses api.ipify.org;
IPv6 is deliberately not published. Static zone files must not also define
these A records. Normal `dns diff` / `dns sync` use the same dynamic sources,
so a later static synchronization won't put an obsolete address back.

To add a name, configure its source and zone in `dns/config.yaml`, remove any
conflicting static A record, and include its zone in `ddns.service`'s zone list.
For another apex, reuse the `''` source; for another label, define a source with
that label. Run from Newport, not a remote host whose public IP is different.
Automation reconciles whole selected zones: review static changes before
editing these zones in the live checkout, since the next tick applies them too.
It uses the existing SOPS-backed DigitalOcean credentials through `cli.py`.

Review before applying:

```sh
uv run --script ~/infra/cli.py dns diff jackharrhy.dev. cheesetown.rocks.
```

Install/update user units:

```sh
install -m 644 ~/infra/hosts/newport/ddns/ddns.{service,timer} ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now ddns.timer
systemctl --user start ddns.service
systemctl --user status ddns.timer ddns.service
journalctl --user -u ddns.service -n 40
```

The old `craft-ddns` units are retired. DNS does not configure router port
forwarding or prove Internet reachability of Minecraft or other services.

# Sven Co-op

Independent Compose project; the main Newport fleet refresh does not manage it.
Map archives/assets stay in `/mnt/terrabud/games/svencoop`, outside Git.

## Setup

From the repository root, with the usual Newport SOPS/age key:

```sh
sops hosts/newport/svencoop/secrets/server.enc.yaml
(umask 077; ./scripts/render-secrets.sh newport/svencoop)
cd hosts/newport/svencoop
python3 install-maps.py ressya_no_tabi
docker compose config --quiet
docker compose up -d
```

`secrets/server.enc.yaml` owns the password, HTTP FastDL origin and admin IDs.
Edit it with SOPS and render again; `.runtime-secrets/server.env` is generated,
ignored plaintext, mode600. The parent `newport` render also includes this project.
`SVENCOOP_ADMINS` contains a dotenv-quoted string with escaped `\n` separators;
keep that quoting because the shared renderer does not quote multiline values.
Passwords accept letters, numbers, dot, underscore and dash.

The entrypoint creates private config as the image's UID999, which cannot read
host-owned mode600 files directly. RCON is disabled; cheats are admin-only.

## Maps

`startup.cfg` and `mapcycle.txt` select Train Travel (`ressya_no_tabi`). Keep startup
map names quoted: the engine's direct `+map` parsing truncates hyphenated names.
`server.cfg` contains ordinary server settings.

`maps.json` records source URLs, SHA256 and archive prefixes. Install either pack:

```sh
python3 install-maps.py ressya_no_tabi fail-mountain-20260531
```

The Python3.11+ installer verifies cached/downloaded archives before extraction
and rejects traversal/symlink entries. Investigate a checksum mismatch rather
than changing the expected hash. Add whole packs, not just BSPs: models, sounds,
scripts and replacement lists may be required. Preserve author map configs.

## Operations

Containers: `svencoop` and `svencoop-downloads`. Both track `:latest`, use
unless-stopped and disable Watchtower. Image updates require explicit pull/recreate.

- Game: UDP27015. FastDL: HTTP on TCP27015, serving only `custom/` read-only.
- Tailnet: `100.123.66.70:27015`; LAN: `10.0.0.80:27015`.
- Public WAN IP can change; update the encrypted FastDL origin accordingly.
- Existing router rule: `svencoop-fall`, ID6, TCP/UDP27015 to10.0.0.80.

Stop with `docker compose stop`; inspect with `docker compose ps -a` and
`docker logs --tail 100 svencoop`. Leave forwarding in place unless asked to
remove it. For an occupied server, install assets then issue
`changelevel "BSP_NAME"` through Docker stdin instead of recreating the container.

Check `sh -n entrypoint.sh` and `docker compose config --quiet`. Actual play
readiness needs A2S queries and an external HTTP BSP/hash check.

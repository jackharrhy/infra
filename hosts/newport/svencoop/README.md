# Sven Co-op

Standalone Newport Compose project, like the nested Cheesetown deployment. It is
not included in the main Newport stack or the fleet CLI's ordinary refresh.

Configuration lives here; map archives, extracted assets and verification records
stay in `/mnt/terrabud/games/svencoop`. No game content belongs in Git.

## Prepare and run

From this directory:

```sh
install -d -m 700 .runtime-secrets
cp server.env.example .runtime-secrets/server.env
chmod 600 .runtime-secrets/server.env
# Edit server.env: choose a password and set the public HTTP FastDL origin.
python3 install-maps.py crimecity2
docker compose config --quiet
docker compose up -d
```

The existing Newport configuration was migrated privately, so its password,
FastDL origin and administrator IDs do not need recreating. It remains stopped
until explicitly started.

`server.env` is ignored plaintext runtime configuration, not something to commit.
If sharing it through this public repository becomes necessary, use the existing
SOPS convention. The entrypoint writes private game-owned config files at startup
and then executes the original image launcher. This avoids giving the image's
UID999 access to host-owned mode600 files. Passwords currently accept letters,
numbers, dot, underscore and dash; FastDL uses HTTP, not HTTPS.

The public `server.cfg` contains ordinary settings. `startup.cfg` selects the map;
`mapcycle.txt` controls rotation. Both currently select Crime City2. Keep map names
quoted: direct startup `+map` mishandles hyphenated names in this engine.
Administrator IDs come from `SVENCOOP_ADMINS` in the private environment file; a
quoted multiline value supports multiple IDs. Existing admin-only cheats remain
configured; RCON is disabled.

## Maps

`maps.json` records the source page, exact archive URL, SHA256 and packaging prefix
for The Train Travel, Fail Mountain and Crime City2 e2. For example:

```sh
python3 install-maps.py ressya_no_tabi fail-mountain-20260531 crimecity2
```

The installer reuses cached archives, verifies their hashes before installation,
rejects traversal/symlink entries and preserves all public assets. Crime City2's
extra `crimecity2/` packaging folder is stripped. A checksum mismatch stops rather
than replacing the expected hash or silently retrying; investigate/remove the bad
cached archive before downloading again. Python3.11+ is required; no dependencies.

To add a map, review its SCMapDB download, add its exact metadata/checksum, install
it, then update startup/mapcycle configuration. The `.res`, models, scripts, sounds
and textures are part of the map, not optional BSP-only downloads.

## Network and console

- UDP27015: game.
- TCP27015: nginx FastDL, not game TCP or RCON.
- Tailnet address: `100.123.66.70:27015`.
- LAN address: `10.0.0.80:27015`.
- Public address: inspect the router/current WAN IP; it can change. Keep the private
  FastDL origin consistent with it.

Use `password YOUR_PASSWORD; connect ADDRESS:27015` in the client console, or
`+password YOUR_PASSWORD +connect ADDRESS:27015` as Steam launch options.

The existing gateway rule is `svencoop-fall`, ID6, TCP/UDP27015 to10.0.0.80.
It was deliberately left enabled while the server is stopped. Do not recreate it
or alter unrelated rules blindly. Gateway automation is outside this project.
FastDL serves only `/mnt/terrabud/games/svencoop/custom`, never private settings.

For a live map change, install assets first, then use the existing Docker stdin
console to issue `changelevel "BSP_NAME"`; don't recreate an occupied server just
to change maps. Preserve author configs. Docker container names retain their old
`svencoop-train` / `svencoop-train-downloads` names for continuity.

## Stop and verify

```sh
docker compose stop
docker compose ps -a
docker logs --tail 100 svencoop-train
```

Stopping does not remove forwarding. Leave it in place unless explicitly asked
to remove it. Both containers use unless-stopped and opt out of Watchtower.
There are no new boot jobs, router controllers or automatic map downloads.

Validate changes with `python3 -m unittest discover -s . -p test_setup.py -v`,
`sh -n entrypoint.sh`, and `docker compose config --quiet`. Actual play readiness
requires local/external A2S queries and an HTTP BSP download/hash check; passing
setup tests alone is not a claimed player join.

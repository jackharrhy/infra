# Fabric configuration

Pins and hashes: `../fabric-mods/runtime-manifest.json` and
`../fabric-mods/datapacks-manifest.json`. itzg copies mods to `/data/mods` and
these configs to `/data/config` at startup.

Provision JARs outside the checkout, from the repository root:

```sh
uv run scripts/provision-cheesetown-mods.py --custom-dir /path/to/custom-builds
```

Build production JARs at the manifest commits, from each mod's repository root:
- Storefront: `./fabric/gradlew -p fabric build`
- ItemSorter: `./gradlew -p fabric build`

Bundled libraries and web resources must remain private to each mod to avoid
Fabric classloader collisions. Do not deploy smoke or thin artifacts.

AudioPlayer media lives in `world/audio_player_data`. Image2Map URL-fetch commands
require operator access. Install Vanilla Tweaks' inner datapack ZIPs in
`world/datapacks`, not the outer download bundle.

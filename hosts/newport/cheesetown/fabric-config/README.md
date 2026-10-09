# Fabric configuration

Minecraft 26.2, Loader 0.19.5, launcher 1.1.2, Java 26.

- World: `/mnt/terrabud/docker-data/newport/cheesetown/fabric-data`
- Mod source: `/mnt/terrabud/docker-data/newport/cheesetown/provisioned-mods`
- Mod pins and hashes: `../fabric-mods/runtime-manifest.json`
- Datapack pins and hashes: `../fabric-mods/datapacks-manifest.json`

itzg copies mods to `/data/mods` and these configs to `/data/config` at startup.

```sh
uv run scripts/provision-cheesetown-mods.py --custom-dir /path/to/custom-builds
```

Build custom mods at the manifest's exact commits. From their repository roots:
- Storefront: `./fabric/gradlew -p fabric build`
- ItemSorter: `./gradlew -p fabric build`

Use production JARs, not smoke or thin artifacts. Their bundled libraries and
web resources must remain private to avoid Fabric classloader collisions.

AudioPlayer media lives in `world/audio_player_data`. Image2Map URL-fetch commands
require operator access. Vanilla Tweaks uses the three inner datapack ZIPs in
`world/datapacks`, not the outer download bundle.

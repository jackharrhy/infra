# Jack Harrhy's Garden

The personal site is the independent Remix app in [`jackharrhy/tea/apps/garden`](https://github.com/jackharrhy/tea/tree/main/apps/garden). The original [`jackharrhy/jackharrhy.com`](https://github.com/jackharrhy/jackharrhy.com) repository remains a pointer with its Astro history intact. The `jackharrhy` Compose service retains all existing domain aliases, Traefik priority, and the Last.fm secret file. It listens internally on port 4322. Do not change the higher-priority routes on the personal domain when deploying the garden.

## Code and writing are separate releases

Tea's `Publish Garden` workflow publishes the application-only `ghcr.io/jackharrhy/tea-garden` image. Updating that image does not publish anything from the local Obsidian vault. Production reads public Markdown from `hosts/mug/volumes/garden-content/current`, mounted read-only at `/app/data/current`. Keep the personal vault off the server and out of container build contexts.

From Tea, export an immutable snapshot with `GARDEN_COMPARE_URL=https://jackharrhy.com npm run content:export --workspace @tea/garden`. Review its added, changed, and removed pages before publishing. The manifest records only media referenced by public pages. Upload those media files to the existing `jacks-garden:jacks-garden` rclone destination and verify them at `https://garden.jack.camera`; do not automatically upload the entire private assets directory. The app's legacy `assets:*` commands are available for deliberate bucket maintenance.

Then run `uv run scripts/publish-garden.py SNAPSHOT --assets /absolute/path/to/vault/Assets` from this repository. It rechecks all source and referenced-media hashes, shows the production diff, asks for confirmation, uploads only referenced assets, transfers an immutable release, activates it with a symlink rename, and restarts only `jackharrhy`. It requires Python, rclone, SSH access to Mug, and an already deployed Tea Garden image. Use `--dry-run` to validate and preview without mutations. A content release does not build or deploy an image.

To update code, pull the selected image and run `docker compose up -d --no-deps jackharrhy` from `hosts/mug`. Keep the prior image and content release for rollback. Do not run an unscoped `infra refresh` for this site.

## Verification and rollback

Before a cutover, start the candidate image against the public snapshot on a loopback-only port, without Traefik labels. Verify `/healthz`, all public page routes, all three feeds, the browser entry and spinning mug, a representative media redirect, `/home`, the 404 status, and development-route rejection. Suppress analytics while testing. Compare browser captures against the Astro baseline at desktop/tablet/phone widths.

For a content rollback, atomically repoint `current` to the previous relative `releases/...` path, then `docker compose restart jackharrhy`. For the initial Astro rollback, restore the `jackharrhy` service's old image and internal port 80 from the saved pre-cutover Compose file and run `docker compose up -d --no-deps jackharrhy`. Preserve unrelated remote Compose edits. The backup image must remain tagged until the migration is accepted.

The initial snapshot preserves all 124 deployed note hashes. A newer local `Fonts.md` was intentionally left unpublished. It contains 241 referenced media entries; the old manifest listed all 425 assets, including unreferenced ones. Existing media stays in R2; the migration does not delete bucket objects.

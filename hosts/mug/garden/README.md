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

## Initial rollover receipt (2026-11-11)

Tea #78 published image revision `f287288b36d371718dadf7fa37c0a7fc688f2982`, index digest `sha256:80ac28118b4391b713a16ec2ce63b9d446f2c7b64f01b84d09a8e47368a50d09` (amd64 manifest `sha256:1ca73638b453868360d2a7a9252027f452daa7c342c3654015fe975b564ae86d`). Mug now follows `tea-garden:latest`; no rollout pin or Watchtower exclusion remains on the site. Watchtower was healthy after the scoped replacement.

The initial release is `volumes/garden-content/releases/20261111-cutover`; `current` points there. All 124 transferred source hashes were verified on Mug. Rollback files are in `~/tea-garden-rollback-20261111/`, and image `tea-garden-rollback:astro-20261111` retains the original image ID `sha256:a8d1df03a0a514d356c12a39bec94eef6a4afdb5996bb5dbf22011389a8fc456`. Keep this first legacy backup. The stopped, never-started `tea-garden-astro-rollback-20261111` container anchors that image against unused-image cleanup; it has no published ports or running process. The tag alone had disappeared after cleanup, so the exact image was recovered from the original registry and its ID reverified during the performance follow-up.

Both primary domains passed `/healthz`, all 124 public page status/text/link comparisons passed after cutover, feeds retained their 10/1/0 items, private development routes returned 404, and the public browser entry ran without console errors. Thirty staged desktop/tablet/phone captures matched layout and text with thumbnail/raster noise below 0.04%. All 18 tests on the feature branch passed on Linux, including the new content publisher tests. No R2 uploads, deletions, or writing changes were part of the rollover.

The live Compose file already had unrelated local edits. Only its `jackharrhy` block was replaced, after comparison with the saved pre-cutover block; no Git reset, full-file checkout, dependency restart, orphan cleanup, or broad pruning was used. The source repo remains public and unarchived, with a README pointer and `astro-before-tea-20261111` history tag (standalone #53).

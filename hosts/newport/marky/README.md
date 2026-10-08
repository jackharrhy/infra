# tea/marky on Newport

`marky` in `../compose.yml` serves `md.jackharrhy.dev` through Newport Traefik and Mug's tailnet origin route. It uses the Tea image at port 44100. Keep the image at a reviewed digest after the first publish. The container runs as `node` and writes Markdown and Discord sessions under `/mnt/terrabud/docker-data/newport/marky_tea`, mounted as `/app/data`. This is a new store; the retired `marky.jackharrhy.dev` route had no running service or data volume.

Render only `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET`, `DISCORD_GUILD_ID`, and `SESSION_SECRET` from `../secrets/marky.enc.yaml` into `../.runtime-secrets/marky.env` with mode 0600. The optional bot token currently cannot read guild roles and is omitted; Marky uses stable palette colors instead. Do not include the legacy `MARKY_GIT_PAT` unless a Git-backed content checkout and `MARKY_GIT_REPO` are configured. The application sets `MARKY_AUTH=discord`, `MARKY_BASE_URL=https://md.jackharrhy.dev`, and persistent content/session paths.

The Discord OAuth application must permit `https://md.jackharrhy.dev/auth/callback`. Confirm this in the Discord Developer Portal before accepting a sign-in smoke. Anonymous mode must not be used on the public host because it permits anyone to edit all files.

From `hosts/newport`, run `docker compose config --quiet`, then `docker compose up -d marky`. Check that `/` redirects to `/auth/sign-in` and `/ws` rejects an unauthenticated upgrade. Mug reads its dynamic route from `hosts/mug/traefik/dynamic/newport-origin.yml`; deploy that file on Mug to publish the hostname.

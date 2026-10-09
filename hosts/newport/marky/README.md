# Marky on Newport

`marky` serves `md.jackharrhy.dev` on port 44100 through Newport Traefik and Mug.
Content and Discord sessions live in `/mnt/terrabud/docker-data/newport/marky_tea`.

Render `../secrets/marky.enc.yaml` to `../.runtime-secrets/marky.env`.
Discord OAuth requires `https://md.jackharrhy.dev/auth/callback`.
Keep `MARKY_AUTH=discord`; anonymous mode allows public editing.
`MARKY_GIT_PAT` is only needed with a Git-backed content checkout.

# Tea Letters to Steve on Newport

`steve` serves `steve-letter-writ.ing` from `ghcr.io/jackharrhy/tea-letters-to-steve:latest`. Watchtower updates the image after Tea publishes from `main`.

- Store: `/mnt/terrabud/docker-data/newport/steve_tea_data` (`letters.sqlite` and `uploads/`)
- Credentials: `../.runtime-secrets/steve.env`
- Manual refresh: `infra refresh newport --service steve`

The source volume at `../volumes/steve` is retained as a rollback copy. A rollback requires stopping the Tea container before routing the old image to that volume; copy any intervening writes first. Keep the database and uploads together.

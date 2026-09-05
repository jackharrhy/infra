# Radio on local Celld storage

Radio uses [our Celld fork](https://github.com/jackharrhy/celld), with its runtime
image pinned by digest in Radio's Dockerfile. This Compose file pins the tested
Radio image separately. Follow the fork's [release and upstream-sync procedure](https://github.com/jackharrhy/celld/blob/main/FORK.md)
before promoting either pin. Watchtower does not update Radio automatically.

The `radio-celld` service owns its network and Traefik labels. Its persistent
volume is `hosts/mug/volumes/radio_celld`, containing:

- `object-store/objects.sqlite3`: authoritative object store, including audio,
  deployments, cell snapshots, and recovery records.
- `object-store/objects.sqlite3-wal` and `-shm`, when present: SQLite state that
  must stay with the database.
- `object-store/objects.sqlite3.runtime.lock`: the runtime/migration lock;
  never unlink it while either could be running.
- `state/`: Celld's local replica directory, separate from the object database.

The runtime uses bucket durability, one CPU, and 1 GiB memory with no swap. This is one node
on one host; a second host with a database copy is a separate authority.
The historical `radio-minio.env` name remains for the existing encrypted secret
source and application password/session secret. Local storage needs no Azure or
MinIO service. Do not run `scripts/migrate-radio.mjs` for this backend change;
that script belongs to the older application migration.

## Deploy an image update

Before promoting a Celld update, build the Radio image and run Radio's real
container smoke with `--image IMAGE --upload-bytes 1073741824`. It checks a full
1 GiB upload and cold recovery with one CPU, 1 GiB memory, and no swap. The
smaller CI host-process smoke does not replace this gate. Update the pinned
Radio image in Git after qualification, then on `mug`:

```sh
cd /home/jack/infra
git pull --ff-only
cd hosts/mug
docker compose config --quiet
docker compose pull radio-celld
docker compose up -d --no-deps radio-celld
```

Compose allows 90 seconds for a graceful final durability barrier. Check the
service health and `https://radio.jackharrhy.dev`, then sign in and check the
room, queue, and audio playback. Only this service needs a restart.

## Backup and restore

Stop `radio-celld` gracefully and stop deploy/operator jobs before taking a
backup. Confirm the final durability barrier in its logs. Archive the complete
`volumes/radio_celld` directory, Compose configuration, rendered secrets, and
exact image digest into a private backup directory. Hash the archive and copy
it off the host. A live copy of only `objects.sqlite3` is not a backup procedure.

Restore while all writers are stopped, with the same image/configuration and
filesystem ownership. Keep the database and any WAL together. To test recovery
from the object store, use a separate working copy and an empty replica
directory; retain the original backup unchanged. A backup restore loses later
writes. There is no automatic recovery from loss of this host's disk.

## 2026-09-05 backend cutover

The stopped Azurite source was copied through `celld-store-copy` into SQLite,
preserving the complete logical namespace and object metadata. Exact keysets,
sizes, attributes, and SHA-256 hashes were verified for 1,037 objects containing
3,531,862,717 bytes. A cold restore with the original Worker verified the room,
all 41 tracks, full audio hashes, HEAD requests, and 164 ranges before cutover.

Private backups on both `mug` and `newport` are under
`/home/jack/backups/radio-local-20260905T2019Z/`. `radio-before.tar` contains the
stopped Azurite and Celld directories, old Compose file, and rendered secrets;
`SHA256SUMS` verifies it. `image-manifests.txt` records the old images. Keep this
directory private. The pristine migration database and detailed manifest are
also retained on `newport`. The original `volumes/radio_azurite` data on `mug`
remains available, with its service stopped.

Once the new runtime has started, the old Azure snapshot is stale. Returning to
it discards subsequent writes. A lossless reverse migration requires stopping
Radio and using the fork's [offline copy procedure](https://github.com/jackharrhy/celld/blob/main/docs/store-copy.md)
from SQLite into a fresh Azure namespace, verifying it, and starting with a
fresh replica directory. Never run both histories as active services.

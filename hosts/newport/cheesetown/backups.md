# Backups

Every six hours, `backup` flushes the server and creates a tar archive. After a
successful backup, `retain-backups.sh` keeps:

- Every backup from the last seven days.
- The first backup of each day from seven to 28 days old.
- The first backup of each ISO week beyond 28 days, indefinitely.
- The earliest surviving rolling backup, indefinitely.

Dates use Newfoundland time. Only top-level `cheesetown-*.tar.gz` files in
`backups/` are pruned. Deployment, retirement and upgrade archives are untouched;
these include the earliest surviving archive, from September 14, 2026.

Preview without deleting anything:

```sh
docker compose exec backup /retain-backups.sh --dry-run
```

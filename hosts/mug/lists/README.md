# Lists

Canonical application: `jackharrhy/tea`, `apps/lists`.
The service keeps `https://lists.jackharrhy.dev`, port 8080 and `/webhooks/ses`.

Runtime configuration is rendered from `secrets/lists-tea.enc.yaml` to
`.runtime-secrets/lists-tea.env`. The six central Auth fields replace standalone
owner/password/API-token bootstrap. AWS, SQS, S3, SES and media configuration stays
unchanged. Silicon Harbour has a separate, list-scoped machine credential.

Data lives in `volumes/lists_tea_data`; verified SQLite update snapshots live in
`volumes/lists_tea_backups`. The Bun pre-update hook returns 75 on backup failure.
Mug Watchtower lifecycle hooks must be enabled for that guard to execute.

Do not refresh this service into an empty volume. Initial migration requires a
source drain, fresh consistent backup/export, complete reviewed human/service
mapping and no-overwrite import into a fresh destination. Keep the original
`volumes/lists_data` and legacy encrypted configuration as recovery points.
Never run both worker sets concurrently.

After migration, refresh only the intended service through the fleet CLI. Use an
explicit verified digest during controlled cutover, then restore the normal
`latest` tracking reference after production app and consumer acceptance. Do not
revoke the old Silicon Harbour token or archive the standalone source repository
before those live acceptance gates pass. Rollback after new writes requires data
reconciliation, not restoring an old SQLite snapshot over current state.

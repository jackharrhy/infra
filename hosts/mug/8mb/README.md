# 8mb

The Harrhy Node 26 app serves https://jackharrhy.dev/8mb/ through Mug Traefik. Video processing stays in the browser; there are no media mounts or upload endpoints. Source: `jackharrhy/harrhy`, workspace `apps/8mb`.

Production follows `ghcr.io/jackharrhy/8mb:latest`. The corrected default-command image is deployed, and the temporary SHA hold is removed. Harrhy owns the short-name publisher; Mug Watchtower remains operational.

## Runtime and privacy

The app runs as UID/GID 1000, with a read-only root, dropped capabilities and one writable mount: `./volumes/8mb-diagnostics:/app/data`. Create that directory as UID 1000 with mode 0700 before recreation. The command sets umask 077, giving SQLite and its sidecars mode 0600. `APP_ORIGIN=https://jackharrhy.dev` constrains optional diagnostics to the canonical origin.

The image now directly invokes Node: PR96 fixed the former npm PID1 wrapper, and the exact published successor passed a real diagnostics POST and Docker SIGTERM test with exit0 and no WAL sidecars. Compose retains a direct-exec umask077 launcher solely for private SQLite file modes, not as an updater hold or pending lifecycle workaround.

The exact telemetry checkbox defaults off. Accepted diagnostics contain only daily aggregate counts, retained for seven UTC dates, with no public read endpoint. These disposable aggregates are deliberately excluded from durable backups. Mug Traefik has no access logging enabled, and the app does not log requests or media details.

## Acceptance and recovery

The exact published image passed local and public Chromium tests: a generated 755769-byte MP4 compressed below 0.1 MB, threaded FFmpeg WASM exported audio, consent off sent no POSTs, consent on returned 204, opt-out survived reload, and there were no page errors. No private media was copied or mounted. This does not establish a 70 GB Windows result.

The previous accepted immutable image and compact legacy image/config recovery remain separate from normal tracking. Do not assume local rollback tags survive an explicit Docker prune. Restore only the intended 8mb configuration/image and preserve the private aggregate directory and unrelated Compose changes. Routine refresh does not authorize volume or recovery-data deletion.

Primary's current rollout receipt is `/home/jack/.local/state/8mb-harrhy-migration/primary-runtime-acceptance.json` on the controller. The standalone GitHub repository has been deleted under explicit authorization; the canonical application/package and compact source-history bundle are retained.

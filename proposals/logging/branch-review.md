# Existing branch review

This source proposal supersedes the design, not the history, of `origin/vic-auth`
(`8a8de64ce720a04baf89dd80e757761199ec155e`, 2026-06-26). That branch remains
unchanged. The proposal is based on current `origin/main`, not a merge or checkout
of the dated branch.

Useful concepts retained: per-host collection, host/service enrichment, structured
JSON-line ingestion and compressed transport. Changes from the old design:

| Dated proposal | Current review direction |
| --- | --- |
| Central storage on Mug, 30-day retention without size target | Newport, explicit 7-day retention and 8 GiB advisory partition-deletion threshold |
| Public `logs.jackharrhy.dev` and new Authelia at `auth.jackharrhy.dev` | Proposed private `logs.pi.jackharrhy.dev`; no new issuer or changes to current JackAuth |
| Unauthenticated Tailnet database listener | Backend not routed directly; separate TLS writer and owner-query policies required |
| Root floating Vector, Docker API socket and entire Docker root | Version/digest-pinned collector with explicit source mounts, no Docker API; permissions still need qualification |
| Unqualified native coverage | Native unit allowlist and cursor/permission validation explicitly deferred |
| No bounded outage policy | Persistent bounded blocking buffers; local source retention can still cause loss |

The old Authelia hostname would collide with the current Auth service. A socket
mounted `:ro` does not make the Docker API read-only. Neither pattern is restored.
No old encrypted secret is copied or decrypted. New credentials are placeholders,
not provisioned secrets. No live route, DNS, certificate, daemon setting or service
has been changed. All proposal files are outside deployment discovery under
`proposals/logging/`; review or merging source must not itself activate them.

Local Docker caps are selected-service source proposals. They require a later,
explicitly authorized Compose recreation to take effect. Watchtower preserves
existing HostConfig, so normal image refreshes do not retrofit new logging
options. Existing tighter caps must be preserved; no daemon restart or mass
recreation is part of this review.

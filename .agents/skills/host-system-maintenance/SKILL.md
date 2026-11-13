---
name: host-system-maintenance
description: "Use when maintaining Linux hosts and remote access."
---

# Host and access maintenance

Read [host maintenance](../../../docs/host-maintenance.md) and the relevant
[operations](../../../docs/operations.md) sections before acting. This covers the
host, access server, storage pressure and network/NAS diagnosis—not permission to
perform all of them during an ordinary application refresh.

## Discovery

1. Establish the actual machine, mount namespace, free bytes/inodes and pressure.
   Use `df -hT`, `df -i`, `findmnt`, interval samples and current process/service
   state. Do not infer system state from a saved profile or old inventory.
2. Identify listeners, unit/cgroup ownership, timers/cron, actual executables and
   containers, including stopped-container mounts. Group workers by their owner.
   An independent backend and its terminal viewer have different lifetimes.
3. For packages, inspect executable/package origin, signed sources, preferences,
   `apt-cache policy`, `apt-mark showhold` and the exact proposed transaction.
   Read unfamiliar CLI help and candidate hooks before mutation.
4. For network/NAS work, establish gateway family, complete authenticated state,
   intended exposure, mount/index/account coverage and independent verification.
   Missing permissions are not empty data; a diagnostic scan is not a write gate.

## Execute only the requested boundary

- Keep stopping, permanent retirement, data preservation and disposal separate.
  Recheck exact path/device/inode/symlink identities before approved deletion.
  Measure allocated bytes without double-counting hardlinks or nested totals.
- Do not widen image cleanup to volumes/builders, app maintenance to host upgrades,
  or package work to reboot/firmware/network changes. Preserve designated recovery.
- For a restart-sensitive package, inspect maintainer scripts and actual service
  names/cgroups first. Preserve deliberate HOLD/channel policy. A no-restart
  needrestart setting does not suppress package-owned restarts.
- Preserve remote access, private identities and a usable old binary/state set.
  Restore services/control outside the lifetime being stopped; do not bootstrap a
  competing server or use a fresh agent to bypass a blocked owner or approval.
- Do not reset Tailscale Serve, overwrite subnet route sets, broaden proxy trust,
  change router global toggles or NFS permissions as diagnosis shortcuts.
- Prefer the existing NAS indexed-search CLI; paginate to its declared total and
  report incomplete archive/index coverage. Inspect selected archives read-only,
  not by extracting whole trees into live data.

## Acceptance

Read back package/source policy, effective unit settings, exact workload/route or
path and affected native application behavior. Check fresh access after network
changes. Distinguish configured/running/reachable/authenticated and a candidate
kernel's boot readiness from the currently loaded driver. A signed index refresh
or firmware discovery is not an installed update.

Keep private snapshots and current approvals outside the repository. Extend the
cohesive host/operations guides for new reusable pitfalls; do not copy proprietary
router payloads, NAS results, credentials or a terminal-server incident chronicle.

# Host maintenance

Use [operations](operations.md) for fleet changes and [agent operation](agent-operations.md)
for ownership. A container refresh is not permission to upgrade the host, restart
Docker/Rex, change networking or reboot. Execute approved ordinary substeps without
repeated approval rounds; ask for genuinely expanded or destructive scope.

## Capacity and workload discovery

Start read-only: establish the host, affected mount and namespace, free bytes and
inodes, interval CPU/I/O/memory pressure, listeners, services/timers and Docker
workloads. Full swap is not proof of current paging; `ps` CPU is a lifetime average.
Container-private tmpfs exhaustion is not host root exhaustion. Compare actual
mounts rather than applying a host-wide cleanup to a container's `/tmp`.

Use same-filesystem allocated-byte measurements, deduplicate hardlinks and avoid
summing both parents and their children. Distinguish source, generated builds,
package stores, runtimes, private local state and recovery. Inspect deleted-open
files when `du` and free-space observations disagree. An unreachable metadata path
is a coverage gap, not proof that nothing uses it.

Before authorized deletion, retain an exact allowlist with path/device/inode and
symlink identity, then recheck it immediately. Check process cwd/executable/open
files and running AND stopped container mounts. Idle snapshots and old timestamps
are evidence, not deletion permission. Separate workload stop, permanent retirement,
knowledge retention and data disposal. Never prune broad backup/dependency trees
merely because they are large.

Bound disposable fixture retention: retain canonical private inputs and active
working copies separately, clean successful-run copies through their owner, and
keep failed reproductions only for a concrete unresolved need. Check headroom
before fan-out. Do not turn each test into another permanent full database/media
checkpoint. Protect live Docker data, Steam libraries, swap and backups unless
that storage migration is explicitly in scope.

For approved application logs, verified-inode truncation can release an open log;
unlinking it may not. Docker-owned active logs need native bounded retention and
a scoped recreation, not external rotation behind the daemon. Measure free space
after cleanup settles; directory-size sums are not reclaimed headroom. Preserve
explicit rollback holds; image, builder-cache, container and volume cleanup are
different scopes.

## Packages and signed repositories

Before an approved package operation, inspect the OS/suite, executable resolution,
`dpkg-query -S` ownership, `apt-cache policy`, `apt-mark showhold`, source files,
keyrings and preferences. A candidate found only in dpkg status is not a working
update source. Compare vendor and distribution versions without confusing a
backported security fix with an old unpatched upstream release.

Within approved scope, refresh signed indexes with error mode `any` and inspect
failures; cached metadata does not prove freshness. Simulate the actual intended
upgrade/removal operations, not merely a different harmless command. Preserve
phasing. Inspect package additions/removals, kernel/driver transitions and daemon
restart effects before applying anything. Read each host's actual update script;
similarly named scripts need not have the same cleanup/reboot behavior.

Keep source and key changes narrow. Verify full signing fingerprints and the
vendor's actual suite/layout; not every vendor uses the Ubuntu codename. Preserve
existing sources/keyrings privately, use explicit Signed-By and never disable
signature verification. A source-only repair should leave installed packages
unchanged. After an upgrade, check package consistency, actual runtime versions,
fresh remote access and affected applications separately from reboot requirements.

Inspect candidate maintainer scripts before installing restart-sensitive packages.
Download/extract for inspection without invoking package hooks. `NEEDRESTART_MODE=l`
does not suppress a package's own service restarts; nested sudo can discard it.
When a reviewed operation needs a temporary needrestart configuration, refuse to
overwrite an existing file and remove only the owned override in a finally path.
Snapshot HOLD state and restore it after a specifically authorized held-package
upgrade; neither a hold nor a channel choice may disappear incidentally.

### Docker, kernels and firmware

Patch-only live restore is not a major-version upgrade strategy. If it is used
for a documented supported patch transition, preserve daemon JSON and verify the
running effective value before and after; removing a property alone may not undo
its live value. A major engine upgrade needs a planned stop/resume of the original
containers, with the updater restored last. Do not pull new app images, recreate
all services or change the storage driver merely to replace the engine. Compare
mounts by destination and verify named networks, volumes and new-container API
compatibility; normalize only proved empty-field API differences.

Keep the running kernel and a useful fallback. For a new kernel, check its DKMS
registration, target-kernel module and nonempty initramfs before scheduling reboot;
current `nvidia-smi` says nothing about the new kernel. Bound DKMS's own parallelism
on a shared host rather than assuming MAKEFLAGS controls it. Preserve compatible
CUDA/toolkit lines for the actual GPU, and treat NVIDIA Container Toolkit sources
separately from a broad CUDA repository pin.

Firmware metadata refresh is discovery, not installation. Check device support,
signed update flags, UDisks/ESP discovery and capsule support before changing disk
layout or attempting a flash. Missing ESRT may require vendor intervention. Do
not change Secure Boot or force firmware writes as incidental repair. Reboot and
firmware approval remain distinct from package maintenance.

A host security update does not patch every container or bundled verifier. For a
relevant CA incident, test each actual verifier with a certificate-rejecting case
and normal HTTPS, bounded and with verification enabled. DNS failures/timeouts
are inconclusive; `curl -k` invalidates the test. Broaden host maintenance into
application rebuilds only under the corresponding approved scope.

## Rex and agent-platform access

Use the installed Rex vendor guide and current official
[installation](https://www.superlogical.com/rex/docs/linux/installation),
[remote-access](https://www.superlogical.com/rex/docs/linux/remote-access) and
[shared-server](https://www.superlogical.com/rex/docs/linux/shared-server) guides.
Verify executable/package origin:
Ubuntu's unrelated Perl package can share the name. A live deleted executable is
not a valid reboot launch path. Do not restart a working server just to diagnose
that mismatch.

Inspect actual user/system unit ownership, custom units/drop-ins, enabled links,
process cgroups, sessions and foreground/background programs. Restoring a binary
can activate a previously enabled retrying service. Stock unit names and a custom
user server are not interchangeable; maintainer scripts may restart stock services
even when the intended custom service has another name.

Preserve private state, identity, layout/launch records and exact available old
binary/state recovery. A package version string is not an available rollback.
Understand candidate schema reversibility before assuming a binary downgrade can
read its state. Isolated candidate tests need separate private HOME/state/socket,
no production identity/Tailscale exposure and only disposable programs.

Restarting a terminal server can kill all programs in its control group. Layouts
are not process resurrection. Ensure maintenance control itself is outside that
lifetime; checkpoint actual owners and explicitly reattach selected viewers to
EXISTING native conversations. Do not type into uncertain restored shells or
start duplicate agents. Independently supervised model backends can survive while
their terminal clients do not. Do not resurrect deliberately retired agents.

Managed login-broker access and embedded Tailscale access are separate acceptance
targets. Verify both against the intended server identity when both are in use;
a successful broker connection does not prove the embedded node is ready. Preserve
listener/access policy and installed startup ownership rather than starting a
competing server. Read-only maintenance probes must not autostart another server.

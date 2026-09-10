# Android ARM64 package manager benchmark

User authorized Lyriq1 ZY22J58799 and Lyriq2 ZY22HZPLL8 on 2026-09-09. Preserve OAuth, sessions, workspaces. Both benchmark processes must be app UID, CapEff=0, under PRoot. Host root ADB must not become transaction authority.

On 2026-09-10 the user also authorized Pacman `000501423003390` for all six
application builds and debugging. It began factory-reset, with no TinyAgent and
224 GB available. A fresh development APK was installed; UI-triggered Fedora
preparation completed under app UID 10223 without app ADB pairing or root.
ADB shell UID 2000 installs/stages/observes only. Builds run through the actual
phone-local OpenCode shell API in `/workspace/tinyagent-six-builds`.
The initial shared-root setup and build debugging are functional acceptance,
not fresh-root dnf5/dnfast comparative timings. Keep that distinction in reports.

Discovery: both current images have `/usr/bin/microdnf -> dnf5`. These names are not independent implementations. Obtain real microdnf 3.x separately. Record binary hashes and package versions before timing. dnfast is pinned initially to 35d4a1b; its current executor uses real mount namespaces, and an inability to execute on Stock is a compatibility result, not a timing sample.

Run each candidate on BOTH phones with alternating/reversed orders; do not assign one candidate permanently to one phone. Record Android build/kernel, PRoot bytes/flags, package versions, CPU temperature, power state and competing jobs. Record differences rather than claiming perfectly identical systems.

## Six application workloads and defect control

User-authorized first assignment: Lyriq1 uses dnf5; Lyriq2 uses dnfast. Cross over representative workloads after matching the baseline to separate device effects from manager effects. Workloads: AntennaPod, Tailscale Android, Organic Maps, VLC Android, AppFlowy, and Termux. Pin each upstream commit and derive dependencies from that commit's build instructions; these are workload selections, not yet validated ARM-host build recipes.

Measure fresh Fedora preparation, host RPM provisioning, language/SDK toolchain setup, checkout, and APK build separately. Record actual native host architecture, package NEVRAs, toolchain hashes, elapsed time, peak RSS, exit status, and output APK hashes. Never count existing installed dependencies as fresh provisioning or an unsupported Android ARM-host compiler as a package-manager speed result. Keep benchmark roots/caches apart from user workspaces and OAuth state. Do not replace the active Tailscale VPN package with a benchmark build.

Confirmed dnfast defect: the current image contains `[main]\ntsflags=nodocs`; `repo makecache --repo fedora` exits 1 at main_config.rs before metadata retrieval. The next source-level concern is the executor's mandatory mount namespace, which has not yet been reproduced through a full Stock transaction. Send dnfast defects to the dedicated dnfast worktree task; TinyAgent retains exclusive control of phone execution and APK installation. Accept a fix only with the failing case, policy-preserving patch, regression checks, ARM artifact provenance, and the same phone reproduction passing. Parsing and ignoring nodocs is not a fix.

Separate CLI startup, metadata retrieval/derivation, warm query/solve, RPM download and transaction application. Use the same frozen repository metadata and RPM set for CPU/storage comparisons; measure live network separately. Control derived cache and RPMDB independently. Do not call a run cold if only process state was reset; do not globally drop page cache or change CPU/thermal policies.

Compare default configurations first, then explicit parallel-download/cache settings. Preserve signature verification and dependency policy. Validate selected package sets and final RPMDB inventory, exit statuses and retry/recovery before accepting a faster run. Keep raw per-run measurements and report failed cells. Prebuilt-image bootstrap is a separate benchmark from package manager performance.

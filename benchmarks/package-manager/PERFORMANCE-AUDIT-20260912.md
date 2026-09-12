# dnfast integration performance audit — 2026-09-12

Scope: `/home/admin/Documents/Codex/2026-09-12/rj/work/tinyagent`, baseline
`624159e5853f153c77e95b75ac464abb6587cb5f`. This is an integration-source audit,
not a complete upstream dnfast audit or proof that dnfast can replace dnf5.
The upstream checkout and recorded full source tar are absent locally.
Follow-up remote check: public `GPLaider/dnfast` is reachable, but fetching the
packaged commit `1449710f35e1079c5999a3d6cc41800d4b432a4d` returns `not our ref`.
Advertised main is `35d4a1b23faec7d28dac7467b0789d981ccf2e3d`. No different source
revision was substituted. Details are retained in `source-resolution.json`.
Existing and concurrently edited application lifecycle/file-provider files were
preserved. No APK, runtime manifest, phone, installed package or RPMDB was changed.

## Implemented and measured

1. `native/fd-gate/executor_fd.c:60`: remove `F_GETFD` and `F_SETFD` after
   successful `dup3(..., 0)`. Linux already clears CLOEXEC on the new target.
   Keep the temporary CLOEXEC copies, including overlapping/reversed sources,
   error cleanup, environment reset and close_range. Exactly `2 * (artifacts + 2)`
   syscalls disappear from each compact handoff. This source is compiled into the
   debug FD probe; the shipped upstream executor ELF is unchanged. The provenance
   JSON now records this local derivative and explicitly says the packaged seed
   was not rebuilt or validated on Android/PRoot.
2. `scripts/stage-dnfast-runtime.py:29`: hash each tar member through
   `hashlib.file_digest` rather than allocating its full contents. All manifest,
   compressed archive and member hashes still apply; output bytes match the
   original implementation. Python 3.11+ is needed, consistent with the existing
   upgrade/collection tooling. The compressed overlay is still held in memory.
3. Follow-up: `benchmarks/package-manager/compare.py` now publishes headline
   time/RSS medians only when measured trial IDs 1–6 are all present exactly once
   and all six exit successfully. Failed and incomplete cells have null medians,
   explicit status/counts, and retained raw output/exit records. Warmup is still
   excluded, with its exits exposed separately. This is measurement correctness,
   not a newly measured performance gain.
4. `scripts/upgrade-dnfast-empty.py`: explicitly close the compressed input buffer
   and release `overlay` after every decompressed member is verified. Remove each
   processed payload from the pending dictionary. This preserves the full
   validate-before-write phase, publication order, durable backup and final hash
   verification while shortening buffer lifetimes.
5. `native/dnfast-launch.c`: try the existing directory first and call mkdirat
   only after ENOENT. Retain nofollow, owner/mode checks and fsync(parent) even
   on the existing-directory path. This removes five failed mkdirat calls from
   a warm state traversal while adding five failed openat calls on first creation.
   Separate Android candidates have now been cross-built as described below;
   packaged assets remain unchanged.

Host: Linux 7.1.6-400.asahi.fc44.aarch64+16k, aarch64, UID1000, 10 logical CPUs.
Compiler/Python versions, affinity, source hashes and raw trials are in the JSON
reports. Warm page cache, fresh process per batch, alternating before/after order;
no CPU pinning or thermal isolation. These are host measurements only.

### FD preparation (9 batches per variant and artifact count)

| Artifact FDs | Before median µs | After median µs | Speedup | fcntl calls before → after |
|---:|---:|---:|---:|---:|
| 0 | 1.993 | 1.388 | 1.44× | 6 → 2 |
| 1 | 2.792 | 1.895 | 1.47× | 9 → 3 |
| 16 | 14.655 | 9.241 | 1.59× | 54 → 18 |
| 256 | 205.976 | 128.176 | 1.61× | 774 → 258 |
| 1024 | 822.226 | 511.234 | 1.61× | 3078 → 1026 |

The microbenchmark forwards counted fcntl/dup3 calls to the kernel. It substitutes
only the effective-UID gate (so an ordinary user can exercise the code) and final
exec destination. Timed batches reuse harmless `/dev/null` descriptors and exclude
process startup and actual exec; allocator/environment/FD-table warmup is excluded.
This does not measure package opening, payload verification, disk throughput,
SELinux, PRoot syscall overhead or actual dnfast transactions. At zero artifacts
the saving is about **0.605 µs**, not a material end-to-end dnf5 replacement gain.

Independent strace, 16 artifacts, 20 warmups plus 1000 iterations: fcntl
**55,080 → 18,360**, dup3 **18,360 → 18,360**, close_range **1,021 → 1,021**.
Traced wall time is intentionally not used in the performance table.

### Real pinned overlay staging (7 processes per variant)

| Metric | Before median | After median | Interpretation |
|---|---:|---:|---|
| Peak RSS | 49,744 KiB | 39,216 KiB | 10,528 KiB / 21.2% less |
| Elapsed | 153.698 ms | 155.644 ms | 1.27% more; no speed improvement claimed |

The runner executes each version of the actual staging script in isolated trees,
including decompression, all hashes and output writes; validation of output bytes
is outside the timed interval. Input overlay: **17,152,687 bytes compressed**, 33
regular members totaling **39,354,618 bytes**, largest member `usr/bin/dnfast`
**8,791,825 bytes**. No fresh-cache or durable-write throughput claim is made.

## Tests and reproducible commands

### Android cross-build follow-up

The modified launcher and FD probe now compile successfully for Android API 30
using the project's pinned ARM64-host NDK r29 rebuild. The 192,051,660-byte archive
was downloaded into this task's work directory and verified against
`fcc3b0ba65318317899fc296df0c5795d472a0cc3870b6fbf659939c1dde63ca`.
This is the existing project's third-party toolchain choice, not an official
Google-distributed ARM64-host compiler. Compiler hash/version and source hashes
are recorded in `android-native-build/report.json`.

Both before and after versions of `libdnfastlaunch.so` and `libfdgate.so` passed
`--target=aarch64-linux-android30 -std=c11 -O2 -Wall -Wextra -Werror
-Wl,-z,max-page-size=16384` with no compiler diagnostics. The script checks
Android API macros and ELF headers. Independent readelf checks confirm all four
are AArch64 PIE executables, use `/system/bin/linker64`, have 0x4000-aligned LOAD
segments, and depend only on Android `libdl.so` and `libc.so`.

The build-check script requires a new output directory and writes only source
snapshots, candidate binaries and a report there. It does not invoke the existing
packaging script, overwrite JNI assets, install an APK or execute on a device.
Candidates and exact source snapshots are retained under
`outputs/android-native-build/{before,after}`. This removes compile/ELF uncertainty,
but does not establish Android SELinux, kernel, PRoot or runtime compatibility.

### Launcher state-directory I/O follow-up

The actual `state_directory` implementation was compiled before/after and run
against disposable Btrfs and tmpfs directories. Nine alternating trials per
variant/filesystem; each warm trial batches 500 traversals after initial creation.
First-creation trials each start with an empty root and perform one traversal.
Timings exclude root opening, flock acquisition, root-ID creation, process startup,
memfd creation and exec; this is not complete launcher latency.

| Filesystem / path | Before median | After median |
|---|---:|---:|
| Btrfs existing state | 11.124 µs | 9.599 µs |
| tmpfs existing state | 9.456 µs | 7.957 µs |
| Btrfs first creation | 534.961 µs | 655.837 µs |
| tmpfs first creation | 28.416 µs | 32.458 µs |

The warm path is 13.7% faster on Btrfs and 15.9% faster on tmpfs in this host
measurement. **First creation is slower**, with an added failed openat per missing
component. Btrfs first-creation timings also vary substantially: before
456.253–1368.633 µs, after 490.295–813.879 µs. These overlapping noisy samples do
not isolate the syscall change from storage scheduling. No cold-path improvement
is claimed. This tradeoff favors repeated use of existing state, not one-shot
provisioning. Absolute warm savings are only about 1.5 µs per traversal here.

Both paths retain exactly five fsync calls. Independent strace over 100 warm
traversals plus one initial creation reports mkdirat **505 → 5**, fsync
**505 → 505**, openat **512 → 517** (including process startup). Traced timing is
excluded from the performance table. No durability operation was removed.
Baseline and optimized sources pass the expanded launcher tests: state reopening
retains device/inode and 0700 mode; regular-file, invalid-component and writable
child rejection join the existing locks, ID, symlink and sealed-context controls.
No Android/PRoot or crash-injection validation was performed.

### Upgrade memory follow-up

The actual upgrade function was measured in fresh disposable roots using the
pinned 1449710 new overlay (all 33 files). The two 43b0928 executables provide
realistically sized **synthetic old inputs**; the test child alone substitutes
their hashes in `OLD`. This does not validate or authorize a production migration
from 43b0928, and no installed root was modified.

| Metric, 7 alternating measured trials | Before | After |
|---|---:|---:|
| Child peak RSS median | 101,456 KiB | 74,400 KiB |
| Elapsed median | 203.369 ms | 204.743 ms |

Peak RSS falls **27,056 KiB (26.7%)**. The measured elapsed time rises 0.68%; no
speed improvement is claimed. GNU time measures the child peak independently of
the outer Python runner. Timings include child Python and GNU time startup;
fixture construction and final verification are outside the timed interval.
Inputs/page cache are warm, each root is fresh, and trial zero is excluded.
The fixture filesystem was **tmpfs**, recorded in `dnfast-upgrade-benchmark.json`;
these results are not Android filesystem or cold durable-storage measurements.
Every run independently verified all 33 published hashes, both original backups
and the root ID. The existing upgrade suite passes against both baseline and
optimized scripts, including empty/checked state, unchanged journal bytes,
changed-state rejection, lock contention, unknown ELF, symlink rejection,
interruption/retry and backups.

### Packaged dnfast vs installed dnf5: host CLI startup follow-up

The new host harness verifies the pinned manifest, overlay and all 33 members,
extracts them into a temporary directory and executes only `--version` and
`--help`. Neither command installs or refreshes packages. The packaged CLI is
dnfast 0.1.0 at the manifest's 1449710 revision; installed dnf5/libdnf5 is 5.4.3.0.
Binary and loader hashes, dependency listing, plugin version output, command argv
and supplied environment are recorded in `host-cli-benchmark.json`.

| Metric, 15 measured runs per tool | dnfast | dnf5 |
|---|---:|---:|
| `--help` elapsed median | 3.388 ms | 17.490 ms |
| Elapsed min–max | 2.975–3.659 ms | 16.799–18.569 ms |
| Separate child peak RSS median | 12,432 KiB | 26,016 KiB |
| Measured command failures | 0 | 0 |

Each timing process is fresh; one warmup per tool is excluded and order alternates.
Both commands use an explicit ELF loader and the same isolated HOME and locale.
dnfast uses its bundled library closure, dnf5 uses host libraries and installed
system plugins. System configuration, implementation scope and help output format
differ (dnfast JSON vs dnf5 text). This establishes only observed warm-host help
startup costs; it does not establish package-policy parity, cold startup, solver,
download, transaction or Android/PRoot performance. The 5.16× elapsed ratio must
not be presented as an overall dnfast-vs-dnf5 speedup.

Direct Python `wait4` measured a 23,872-KiB dnfast launch peak that included the
pre-exec Python child image. The harness retains that field only as
`launcher_maxrss_KiB`, and measures CLI RSS separately using GNU `/usr/bin/time`
as a small native parent. The table uses those 15 independent RSS samples.
GNU time wrapper overhead is excluded from the timing medians. The comparison
validates dnfast's terminal schema/exit/errors/help payload and dnf5 usage text;
failed, missing or duplicate timing cells have null medians. RSS failures also
withhold the RSS median and make the runner fail.

### Commands

The Android build check accepts paths to the verified NDK archive and extracted
clang. Use a new output directory on each run:

```sh
python3 -B scripts/check-dnfast-android-build.py --compiler /home/admin/Documents/Codex/2026-09-12/dnfast-performance-audit/work/ndk-inputs/unpacked/android-ndk-r29/toolchains/llvm/prebuilt/linux-arm64/bin/clang --ndk-archive /home/admin/Documents/Codex/2026-09-12/dnfast-performance-audit/work/ndk-inputs/android-ndk-r29-aarch64-linux-musl.tar.xz --output-directory /tmp/dnfast-android-build-new
```

From `/home/admin/Documents/Codex/2026-09-12/rj/work/tinyagent`:

```sh
python3 benchmarks/package-manager/benchmark-fd-handoff.py --output /tmp/dnfast-fd.json
python3 benchmarks/package-manager/benchmark-dnfast-staging.py --output /tmp/dnfast-stage.json
python3 -B benchmarks/package-manager/test-compare.py
python3 -B benchmarks/package-manager/test-host-cli.py
python3 -B benchmarks/package-manager/benchmark-host-cli.py --output /tmp/dnfast-host-cli.json
python3 -B scripts/check-dnfast-empty-upgrade.py
python3 -B benchmarks/package-manager/benchmark-dnfast-upgrade.py --output /tmp/dnfast-upgrade.json
python3 -B benchmarks/package-manager/benchmark-launcher-state.py --output /tmp/dnfast-launcher-tmpfs.json
python3 -B benchmarks/package-manager/benchmark-launcher-state.py --fixture-parent /home/admin/Documents/Codex/2026-09-12/dnfast-performance-audit/work --output /tmp/dnfast-launcher-btrfs.json
cc -std=c11 -O2 -Wall -Wextra -Werror benchmarks/package-manager/fd-handoff.c -o /tmp/dnfast-fd-check
/tmp/dnfast-fd-check --test
strace -qq -c -e trace=fcntl,dup3,close_range /tmp/dnfast-fd-check --bench 16 1000
```

Use unique output paths if those examples already exist. Both A/B runners default
to the immutable baseline above and accept `--baseline` to select another retained
commit. They compile/run only synthetic or pinned-input fixtures, use temporary
directories, preserve failed-test exit status and never invoke package managers.
FD tests need RLIMIT_NOFILE >=8192 for the FD4096 sentinel; the Python runner raises
its own soft limit when the existing hard limit permits it. Run the standalone C
test under the same limit. The timing-only C mode does not require the sentinel.

Verified results:

- **Both FD versions pass 22 controls each:** 15 real-exec cases covering 0/1/16/
  256/1024 artifacts × prompt/yes/no, reversed overlapping inputs, byte identity,
  CLOEXEC survival, high-FD closure, environment and umask; 7 invalid-input,
  non-root presentation, mid-duplication failure, injected dup3 failure and
  descriptor-exhaustion cleanup cases. The real exec targets only the harness.
- **Both staging versions pass:** direct input and installed-APK input produce
  byte-exact assets; corrupt manifest and corrupt compressed overlay are rejected
  without replacing good staged assets. No real installed APK is required: the
  runner builds a temporary ZIP from the pinned local inputs.
- Existing `native/dnfast-launch-test.c` passes lock, stable ID, nofollow, ownership/
  mode, corrupt ID and immutable-context controls. Its generated fixture was removed.
- `native/fd-gate/probe.c` compiles with C11/O2/Wall/Wextra/Werror on this host.
- `git diff --check` passes. Separate Android cross-builds now pass as described
  above; no APK build, device test or native upstream suite was run. Host tests
  and cross-compilation do not attest Android labels or the real root gate.
- Follow-up comparison regression suite: **6 tests pass**, including fast failures
  mixed with successes, all-failed cells, signal exits, missing/duplicate/unexpected
  trials, warmup exclusion, independent cells and preservation of raw evidence.
  A synthetic cell with four 0.01-second failures and two 1.1/1.3-second successes
  reproduced the original misleading 0.01-second median; it now reports failed
  with null time/RSS medians. Synthetic fixture values are not benchmark timings.
- Host CLI suite: **4 tests pass**, covering structured dnfast help acceptance,
  dnf5 help rejection/acceptance, failed/incomplete timing admission and real child
  timeout/reaping. All 15 timing samples and 15 separate RSS samples per tool pass.
  No root privileges or device are required; the pinned harness requires ARM64
  Linux, Python 3.11+ and GNU `/usr/bin/time`.

Timing data preceded only a CLI argument-spelling check in the C harness; both the
timed and final harness hashes are recorded. Final controls and strace use the
final harness; the native implementation and timed loop are identical.

## Remaining findings, ordered by decision value

### 1. Fixed comparison admission; semantic parity remains unverified

The original `benchmarks/package-manager/compare.py:30` excluded the first trial
but included nonzero exits in medians, allowing a fast error to become the headline
time. The follow-up fix now withholds medians for any failed or incomplete cell,
rather than reporting only surviving successful runs. Existing summary consumers
must accept null medians and inspect status. A successful warmup is not required
for the six measured trials to pass; its exit remains visible in warmupExits.
`refresh.py` is explicitly a first compatibility pass, runs one fixed order and
uses live repositories; its dnfast invocation does not set the same candidate
cache override as dnf5/microdnf. Neither result is sufficient for a replacement
speed claim. The follow-up ran only host `--help` using the pinned packaged dnfast
and installed dnf5, as described above. Repository refresh, package-set and
transaction scenarios were not executed or silently reclassified.

Further comparative work must gate each workload on successful semantic output,
pin repository metadata/RPM sets, verify equal
selected package sets and final RPMDB, and separate startup, metadata, solve,
download and transaction time. Follow the existing `PROTOCOL.md` control policy.

### 2. Upgrade buffer lifetimes reduced; full initial materialization remains

The original `scripts/upgrade-dnfast-empty.py:35-48` retained the compressed overlay
and every decompressed member throughout the update. The follow-up now releases
the compressed bytes after verification and removes processed dictionary entries,
with the measured RSS result above. Initial verification still materializes all
payloads. The compressed-plus-decompressed byte sizes at the end of that initial
phase total **56,507,305 bytes (53.89 MiB)**; this is an input-size calculation,
not measured RSS. Old executable buffers and subsequent full-file reads still add
memory. Existing files are read for comparison and again after publication.

A disk-backed verified staging set with streaming file comparisons could reduce
memory, but must preserve validate-before-write, lock coverage, durable backups,
interruption/retry and checked-state binding. This is a larger transaction change;
that larger design change remains deferred. APK generation and rare upgrade costs must be
kept separate from routine dnfast invocation performance.

### 3. Existing-directory mkdir calls removed; fsync retained

The original five child-directory calls each executed mkdirat even for existing
entries. The follow-up now opens existing state without those failed creates,
with both warm and first-creation costs measured above. Five parent fsync calls
remain on both paths: simply dropping synchronization for an existing entry could
alter recovery after an interrupted prior mkdir. Physical flush cost was not
isolated. Measure on the Android filesystem and add crash/retry coverage before
changing that durability contract. memfd fsync/seal/identity checks remain.

### 4. Compact handoff allocation is small; FD headroom is more significant

`executor_fd.c:43-50` uses one calloc of at most 1026 integers: **4104 bytes** on
this host. Allocator elimination was not separately shown beneficial and was not
implemented. All input FDs are duplicated above the final target range before
remapping, which is necessary for overlapping inputs. At 1024 artifacts temporary
FDs can reach 2054 even with a compact initial layout; low RLIMIT_NOFILE remains
a real admission constraint. Failure cleanup is tested, but the algorithm is not
made multithreaded: remapping, close_range, clearenv and umask affect process-wide
state and belong in a dedicated exec process.

### 5. Dependency resolution and metadata parallelization require upstream source

The local `dnfast_native.h` exposes solver/context APIs but has no implementation.
Runtime manifests pin upstream revisions 1449710 and 43b0928 and list libsolv,
libsolvext, librpm and libmodulemd; `runtime/dnfast-target-tree.txt` records
dnfast-solver and vendored ureq 3.3.0. These prove dependencies, not solver runtime
complexity, allocation ownership or current scheduling behavior.

The archival architecture document under
`/home/admin/Documents/Codex/2026-09-06/v/work/resume-github/dnfast/files/docs/architecture.md`
describes single-owner libsolv/librpm objects, verified mmap .solv caches, compact
file-provides shards and generation/cookie-bound reuse. It is contextual evidence,
not verification that the shipped binaries implement every described property.
Do not parallelize a shared solver pool or RPMDB writer from that description.

`DNFAST-HANDOFF.md:71-97` records historical primary/filelists retry and slow-network
failures, including a 14,622,908-byte primary and 44,235,438-byte filelists body.
These are historical diagnostics, not newly reproduced performance results; the
referenced phone evidence and source fixes were not revalidated here. Metadata
download, independent verified decompression/hash work and RPM downloads are
possible bounded parallel stages, provided repository authentication, byte limits,
connection limits, cancellation and deterministic solver inputs remain intact.
Measure frozen-metadata CPU/RSS separately from live-network/power-state effects.

## Changed files and evidence

Owned modifications/additions, all relative to the TinyAgent root:

- `native/fd-gate/executor_fd.c`
- `native/fd-gate/PROVENANCE.json`
- `native/dnfast-launch.c`
- `native/dnfast-launch-test.c`
- `scripts/stage-dnfast-runtime.py`
- `scripts/upgrade-dnfast-empty.py`
- `scripts/check-dnfast-android-build.py`
- `benchmarks/package-manager/fd-handoff.c`
- `benchmarks/package-manager/benchmark-fd-handoff.py`
- `benchmarks/package-manager/benchmark-dnfast-staging.py`
- `benchmarks/package-manager/compare.py`
- `benchmarks/package-manager/test-compare.py`
- `benchmarks/package-manager/benchmark-host-cli.py`
- `benchmarks/package-manager/test-host-cli.py`
- `benchmarks/package-manager/benchmark-dnfast-upgrade.py`
- `benchmarks/package-manager/launcher-state.c`
- `benchmarks/package-manager/benchmark-launcher-state.py`
- `benchmarks/package-manager/PERFORMANCE-AUDIT-20260912.md`

Delivered evidence under
`/home/admin/Documents/Codex/2026-09-12/dnfast-performance-audit/outputs`:
`fd-handoff-benchmark.json`, `dnfast-staging-benchmark.json`, `native-checks.json`,
`fd-handoff-strace-before.txt`, `fd-handoff-strace-after.txt`, this report and a
scoped patch. Follow-up regression results are in `comparison-checks.json`.
Source availability is recorded in `source-resolution.json`; actual CLI samples
and test checks are in `host-cli-benchmark.json` and `host-cli-checks.json`.
Upgrade measurements and safety controls are in `dnfast-upgrade-benchmark.json`
and `upgrade-checks.json`. Launcher samples/checks are in `launcher-state-btrfs.json`,
`launcher-state-tmpfs.json` and `launcher-state-strace.json`, with raw strace text
alongside. Android compiler/source/ELF records are in
`android-native-build/report.json` and `android-native-build/readelf-checks.json`.
The patch now covers eighteen owned files and excludes all other agents' and
pre-existing changes.

# ARM build casebook — provisional

Campaign: AntennaPod, Tailscale Android, Organic Maps, VLC Android, AppFlowy, Termux.
The six-app campaign is incomplete. No general harness rule is promoted by this
casebook yet. Count independent failed executions with retained evidence, not
log polling, repeated explanations or retries that only re-display an old error.
An issue needs at least three verified occurrences and a reviewed common cause
before promotion. A single-app-specific cause remains a case even if its retries
repeat. Keep per-app/toolchain scope, failing command, root cause, fix and rerun
evidence. A cleared stage is not a complete APK success.

## Recorded incidents (occurrence totals not yet audited)

| Case | Scope | Evidence | Result |
|---|---|---|---|
| Missing gperf | VLC prerequisite | PACMAN-VLC-GPERF.md | prerequisite corrected; not a dnfast defect |
| Host FPU probe selects fixed-point NEON | VLC / mpg123 | PACMAN-VLC-ARM-FPU.md | previously failing source compiled |
| Linker transformation corrupts directory | VLC / x264 | PACMAN-VLC-ARM-FPU.md | suffix transformation corrected |
| x86-64 aidl selected on ARM host | VLC / SDK 36 | PACMAN-VLC-AIDL.md | real ARM AIDL compile passed |
| Meson PATH differs on cache reuse | VLC / MediaLibrary | PACMAN-VLC-AIDL.md | pinned cache loaded; full APK pending |
| Android kills app process tree | Pacman concurrent workload | PACMAN-PHANTOM-PROCESS-FAILURE.md | admission/worker checks passed; full stability pending |

## Investigation notes; NOT promoted general rules

Snapshot `evidence/build-campaign/index.json` contains 19 distinct run IDs.
The saved result files and complete logs of terminal runs are retained per ID.
The old VLC run 1789017118644979658 still says running but its recorded PID is
absent; it is not counted as a live job or a terminal success. VLC run
1789042076770305377 subsequently exited 0, but the collector searched the old
module path and reported failed/apks=[]. Its separate artifact verification
records the real APK and phone/host hash; the original report remains intact.
See PACMAN-VLC-AIDL.md. PID presence alone does not
prove identity after PID reuse; retain the process snapshot and command context.

Additional reviewed cases from that snapshot:

| Case | App | Independent run | Cause / evidence |
|---|---|---|---|
| Missing generated icon members | AppFlowy | 1789006666718558420 | generator reports success after `rsync: command not found` at line 731; Flutter later fails on missing generated symbols |
| OpenSSL Perl execution failure | AppFlowy | 1789004520513239138 | `/.l2s/.l2s.perl` path split in shell; current wrapper explicitly selects `/usr/bin/perl`; subsequent run passed Rust phase |
| Unsupported host GOARCH | Tailscale | 1789004518844773292 | pinned gomobile `archNDK` panics on arm64 host; not a Go target-selection or RPM error |
| Custom permission checker ignores ARM override | Organic Maps | 1789001928601220907 | APK assembled, but post-build permission task invokes Maven aapt2 directly; checker corrected to honor override; later full task passed |
| Collector searches obsolete module | VLC / benchmark harness | 1789042076770305377 | build exit 0, real APK under application/app; fixed glob reproducer and ZIP/hash verification passed |

No occurrence total is inferred by grouping all these as "ARM problems".
Their failure mechanisms differ. Promotion remains pending the complete campaign.

## Android builds on the phone: measured lessons

This is an ARM64 Linux HOST building for an Android TARGET. Do not assume a
desktop x86-64 host because the project says Linux. Before invoking downloaded
native tools, inspect `uname -m`, `file <tool>` and that tool's version command.
An existing executable can still fail because its ELF architecture or loader
is wrong. QEMU is not automatically available; do not treat emulation, ADB or
root as a prerequisite for the app-owned Fedora build.

- Read `/opt/tinyagent-build/android-build.json` if present for measured SDK,
  ARM aapt2 and Java paths. Do not guess `/usr/lib/jvm` paths. Use the project's
  Gradle wrapper and inspect its required JDK; Java 17 is not sufficient for
  every wrapper or plugin version. Use `./gradlew --version` to inspect the
  wrapper without evaluating the project's default tasks.
- Maven/Google SDK downloads may replace working ARM tools with x86-64 builds.
  Verify the actual selected aapt2, aidl, NDK clang and other native executables.
  Gradle can use the measured aapt2 through `-Pandroid.aapt2FromMavenOverride=<path>`.
  This does not repair AIDL or an x86-only NDK; verify each independently.
  The bundled SDK setup invokes `configure-arm-aidl.py` and compiles a real AIDL
  interface before reporting success. Inspect `/opt/tinyagent-build/arm-aidl.json`
  when AIDL fails; a version label alone is not a compiler execution test.
- Build ONE large project at a time. Start with one worker: Gradle
  `--max-workers=1`, Make/Ninja `-j1`, Cargo `-j1`, Go `-p 1`. Nested tools may
  ignore the parent's limit: VLC's Meson needs `MESONCOMPILEFLAGS=-j1` as well
  as `MAKEFLAGS=-j1`. Do not spawn another build as a waiting shell. Android
  killed a previous app-owned build process tree under process pressure.
- Preserve build caches. Read the FIRST real failing command and its complete
  stderr, not only the final Gradle/Make summary. A timeout or persisted
  `running` tool record does not prove the process is alive. Check the actual
  PID, elapsed time, CPU activity, log growth and terminal exit record before
  starting a retry. Lack of new output alone does not prove a hang.
- Meson caches depend on the Meson version used to create them. VLC cached
  MediaLibrary setup used bundled Meson 0.63.0; a retry incorrectly selected
  Fedora Meson 1.11.2 because PATH was set only in the first-setup branch.
  Restore the project's pinned PATH on BOTH setup and reuse paths before
  considering cache deletion. Installing the newest Meson did not fix this.
- Cross-compilation probes can misidentify the target. VLC's mpg123 selected
  ARM64 NEON plus fixed-point arithmetic after probing the HOST for FPU support.
  Correcting its Android ARM64 CMake target branch produced REAL_IS_FLOAT and
  cleared that compilation error. Do not delete the decoder's safety check.
- A misleading endian/linker failure can be a path bug. x264's Make expression
  `$(subst ld,,$(LD))` removed `ld` from `/opt/tinyagent-build` as well as the
  linker name. Use a suffix-specific transformation; inspect the resulting
  command path before changing CPU/compiler flags.
- Missing gperf is a host prerequisite, wrong ELF architecture is a toolchain
  issue, and source/CMake/PATH errors are build issues. Do not blame dnfast
  unless dependency resolution, download or RPM installation evidence supports
  that attribution. Install only the missing, task-required prerequisites.

These lessons include the earlier Pacman runs and must not be counted as
completion of the current distributed DeepSeek campaign. In that campaign,
independently verified AntennaPod, Termux and VLC APKs account for 3 of 6;
VLC packages prebuilt native AARs, so native-source coverage remains incomplete.
Tailscale, Organic Maps and AppFlowy remain unverified. Recheck current evidence rather than promising every app
will build. For a fix, keep before/after failure logs, the source diff and the
same-task rerun. Only report APK success after the command exits successfully
and the actual APK exists, has nonzero size and a recorded SHA256. Deliver it
through TinyAgent's file actions below, never an inaccessible private path.

## VLC repeated LOW_MEMORY recovery experiment

Lyriq2 exit-info records two Android LOW_MEMORY kills: PID9297 at device time
2026-09-11 04:51:36.105 and PID3180 at 05:17:22.489. Retained evidence:
`evidence/lyriq2-low-memory-exit.txt`, `lyriq2-low-memory-exit-2.txt`, and
`vlc-app-assemble-before-recovery-2.log`. The second log reaches APK metadata
tasks but contains no verified successful APK completion.

The first retry used one worker with separate Gradle 2560 MiB and Kotlin
1536 MiB heap limits. This does not establish the peak combined resident
memory or prove which process triggered Android's kill. The next experiment
uses a 1536 MiB Gradle heap with Kotlin in-process compilation and one worker,
after checking actual processes/configuration and retaining build outputs.
Guidance is saved in `evidence/vlc-second-lmk-guidance.txt`; it is not yet a
successful recovery result or a promoted general harness rule. Submission is
guarded by verified APK update and an idle existing session.

### Observed recovery, 2026-09-11

Runtime4 was installed over USB without clearing app data. The second recovery
produced `VLC-Android-3.7.2-Beta-1-debug-all.apk` (134155415 bytes).
The existing session's incremental verification returned `REAL_BUILD_EXIT=0`,
`BUILD SUCCESSFUL in 1m 40s`, and 234 up-to-date tasks. This duration is only
the incremental verification, not the original build duration.
An independent USB SHA256 read matched the agent's result:
`31d0616b1d2e92f6dddb2caa2f87861dc3c5da1e3b18436bb057059bc6fb8715`.
Evidence: `evidence/go-campaign/lyriq2-ses_f738df35dffers7C8LrjNYoVg4-1789082603619.json`.
Phone tool output reports apksigner and zipalign exit 0. Native VLC libraries
were packaged from prebuilt AARs; this is not a completed native-source build.
Installation and launch of this APK have not been verified.

Independent host verification of the USB-exported file also passed ZIP CRC,
apksigner and zipalign `-c -P 16 4`. Its signer SHA256 is
`31e6ce48aa6d84279c5e9f6eee443091a9816553f63122191f6d022106568cfa`.
Receipt: `evidence/vlc-independent-apk-verification.json`.
ZIP alignment does not establish ELF segment alignment or runtime behavior.

Observed reporting mistakes to prevent: capture the original background
process exit code in its job record, instead of rerunning a successful build
solely to recover the missing status. A certificate subject such as
`CN=Android Debug` does not identify a signing key; compare certificate
fingerprints before claiming it matches a particular keystore.


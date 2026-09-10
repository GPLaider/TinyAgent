# PRoot parent-death candidate — 2026-09-10

The previous native PRoot can leave its child running after tracer SIGKILL.
The source candidate adds PTRACE_O_EXITKILL to the default options, including
the PTRACE_O_TRACESECCOMP fallback. It does not rely on a userspace exit handler.

## Reproduction and actual device result

Target: Lyriq1 ZY22J58799, transport 100.79.134.53:5555, application UID 10042.
No Lyriq2 operation. Existing OAuth and application data were not cleared.
The debug probe launches its own PRoot and sleep child, verifies process
identity and UID, kills only its owned test parent, invokes the real recovery
method on its isolated test directory, and checks parent/child/marker state.
Its finally block cleans up its owned child even after a negative assertion.

- Baseline in the same APK: round 1 passed, round 2 failed with
  `Child survived recovery`. This is a timing-dependent failure, not a claim
  that every baseline round fails. Evidence: `lyriq1-exitkill-baseline-control.png`.
- Candidate parent SIGKILL: 3 consecutive passes.
  Evidence: `lyriq1-exitkill-parent-death.png`.
- Candidate live recovery/SIGQUIT: 3 consecutive passes.
  Evidence: `lyriq1-exitkill-live-recovery.png`.
- After probes, app-UID ps showed only the application, no test child.
- Main backend then started successfully; before/after snapshots retained all
  34 session IDs, connected provider IDs openai/opencode, and dark theme.
  Evidence: `exitkill-candidate-before.json`, `exitkill-candidate-after.json`.
  This turn did not perform an additional OAuth inference.

## Build and installation provenance

`scripts/build-proot-candidate.py` verifies pinned source archives, applies
`patches/proot-exitkill.patch`, derives all 66 upstream objects plus generated
loader-info, and builds the ARM64 loader and PRoot using NDK 28.0.13004108.
Compilation uses Android API 30 and 16 KiB max-page-size alignment. Both
process_vm and seccomp_filter compile/link checks pass. ELF dependencies were
checked for libtalloc.so/libandroid-shmem.so and absence of host RPATH/RUNPATH.
The missing upstream string.h include for ashmem_memfd is supplied explicitly
for that translation unit, without disabling declaration errors.

Dependency shared objects remain the separately hash-pinned Termux prebuilts;
this is not a source rebuild of libtalloc or libandroid-shmem. ARM32 loader
support is not built or claimed. Source/compiler/script/output hashes are in
`evidence/proot-exitkill-source-build.json`.

APK: `TinyAgent-exitkill-candidate.apk`, versionCode 3, 0.1.0-preview.4.
SHA256: `616137bf1360d0cc841003c66f8fe98b63824f0543ab9894a2a66b2d368b680b`.
The installed base.apk hash matched. Debug signer SHA256:
`a3ef78ae0bfdfc30307e3448e138eca29adf39d966f89af116bbce151abc1ed2`.
`:app:assembleDebug :app:lintDebug --offline --no-daemon` passed.
Packaged candidate native bytes were checked against the source build outputs.

## Initial integration gate

Candidate libraries are deliberately separate debug probe inputs. Production
`libproot.so` and the running main backend still use the baseline. Promote
the validated candidate through native provenance/staging checks, then run
actual Fedora/OpenCode jobs and recovery regression before claiming the
shipping runtime is fixed. Session orphan reconciliation, full seven journeys,
six-app workload completion and release acceptance remain open.

Pacman's existing VLC job was observed with live python/make children and
advancing configure output during this work. It was not restarted or updated.

## Promotion to default runtime

The next APK promotes these same tested bytes into main libproot.so and
libproot_loader.so. `stage-proot.py` still validates the original four Termux
component hashes, then validates and applies the pinned source-built archive.
The phone self-build already calls this script, so it will not silently revert
to the prebuilt tracer. `runtime/proot-exitkill-1.json` records the separation
between source-built PRoot and prebuilt dependencies. Two packaging runs gave
the same archive SHA256:
`5024155ddffb78fdc0fbbd230e38d0612baf66f433e287ba89f212f131d02384`.

The strengthened APK verifier failed on old libproot.so before staging and
passed after rebuilding. Native merge incremental state initially failed with
`DataFile.getItems() ... dataFile is null`; rerunning all Gradle tasks passed
assembleDebug and lintDebug. All 952 GUI asset hashes and runtime/license
checks passed as well.

Installed `TinyAgent-exitkill-promoted.apk` SHA256:
`69a6b1a1a357ed0fb7eb9b7508dd800987ce916d803df86cef463c5ad14d95b6`.
Same development signer and version as the probe APK. Device base.apk hash
and extracted libproot.so hash matched. Default-runtime parent SIGKILL probe
passed 3/3: `lyriq1-exitkill-promoted-parent.png`. The old probe text says
"installed baseline" for candidate=false; here that means the default library,
whose hash is now the patched `4220f05c...`, not the original Termux binary.

Main Fedora/OpenCode startup passed. `exitkill-promoted-before.json` and
`exitkill-promoted-after.json` retain all 34 old sessions, provider connection
IDs and dark theme. Existing OAuth started a Luna integration run in dedicated
session `ses_f75b1e71cffewwPw1HweI7YEYo`; its result is pending at this entry.
This does not close broader release or real job recovery acceptance gates.

### Existing OAuth/Luna actual development result

Session `ses_f75b1e71cffewwPw1HweI7YEYo` finished idle without a model error.
Luna used openai/gpt-5.6-luna to inspect Fedora 44/aarch64, Git 2.55.0 and
Python 3.14.7, then ran three separate source-repair rounds. Each unchanged
test failed with AssertionError/exit 1, calculator.py was patched from a-b
to a+b, and the same test then exited 0. An initial missing QA parent directory
was recovered by the agent. PRoot guest uid=0 was correctly distinguished
from Android app UID 10042.

The host independently fetched all 13 fixture/result files through the real
backend file API. `scripts/check-luna-proot-integration.py` passed all three
rounds, checking tool chronology, actual failure/success logs, test immutability,
source change and result.json consistency. Evidence: session `-probe.json`,
`-files.json`, and `lyriq1-exitkill-luna-complete.png`.
The live process chain was app 26977 → PRoot 27130 → OpenCode 27138, all app
UID 10042. This proves normal Fedora model/tool operation with the promoted
tracer; it does not yet prove recovery of an interrupted real model workload.

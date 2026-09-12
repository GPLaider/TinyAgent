# PRoot ARM64 fchmodat2 correction

Release candidate integration passed build/lint, packaged native/runtime/GUI checks and the existing production signer. APK SHA256 05b4346de52de7b6ea233a0ae758b68a9a1118cf83045c5db974b3af0524cb58, 145215610 bytes, harness20/runtime8. Evidence: `evidence/harness20-apk-candidate.json`. This APK has not been installed on the campaign phones or published. The existing source export predates this native change and must be refreshed before delivery.

Corrected parent-death regression passed: `evidence/proot-cargo-sigkill-fixed-app-uid.json`, APK ff407df3b37d3b518cd1301be25e4cbe52d22d0634f2e2819f5797fa80f85d7d. The tracee heartbeat advanced before SIGKILL and stopped afterward; the tracer exited. Exact archive and syscall checks also passed in this run. Main app PID18677 stayed unchanged. This proves the isolated SIGKILL path, not application-level recovery.

The pinned PRoot 5.1.107.92 omitted ARM64 syscall452. Absolute paths passed to fchmodat2 were not translated into the guest root. An app-UID probe reproduced ENOENT despite ordinary chmod succeeding.

`patches/proot-fchmodat2.patch` adds the syscall mapping and routes it through the existing flag-aware path translation and fake-id handling. It retains the existing EXITKILL patch and pinned dependencies.

Build with `python scripts/build-proot-fchmodat2.py`, then `python scripts/package-proot-candidate.py`. The build verifies the source archive, patches, dependency hashes and ARM64 ELF linkage. The deterministic archive and manifest are `runtime/proot-fchmodat2-2.tar.gz` and `.json`. `scripts/stage-proot.py` stages these native inputs and `scripts/check-packaged-runtime.py` checks their bytes inside the APK.

On Lyriq2 (ZY22HZPLL8), a separate targetSdk36 test APK ran under Android UID10154. With the original Cargo1.85.0 ARM64 archive and device Fedora GNU tar, baseline returned2 with `Cannot change mode ... No such file or directory`; candidate returned0 and the extracted components file matched. Absolute and relative syscall cases, invalid flags and no-follow target preservation also passed. Evidence: `evidence/proot-exact-cargo-app-uid.json`.

The test sources are `tests/proot-chmod/`. Its builder requires the original baseline and candidate ELFs plus the captured Fedora tar/dependency payload and exact uncompressed archive in `.checks/proot-chmod-probe/fedora-tar-root.zip`. It is a device regression fixture, not a standalone source-only build. Original archive SHA256: cdebe48b066d512d664c13441e8fae2d0f67106c2080aa44289d98b24192b8bc.

Parent-death validation is separate: Java destroyForcibly did not produce a confirmed stop within5s; a subsequent test used unsupported Android Process.pid and crashed the test app. Neither counts as a PRoot regression pass. The corrected test obtains TracerPid from procfs and verifies ownership before SIGKILL. Main app PID18677 remained unchanged. Full APK deployment, actual application stop/recovery and the remaining campaign builds are not yet accepted.

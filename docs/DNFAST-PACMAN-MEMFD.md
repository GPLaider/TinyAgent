# Pacman native memfd compatibility failure

## Fix validation: 43b0928

### Product root upgrade and package bridge

APK `a3689c9865a6029cad55c5ea5241000eb42b4f1165c542bec477e8227a2f1927`
adds the empty-state updater. On Pacman the existing product root was upgraded
under an exclusive root flock, with both original binaries retained under
`var/lib/dnfast-upgrades/16c6887-to-43b0928/<root-id>`. Its unchanged root ID is
`34a4b43fa4d4d3bc013f0682e535f2ff64c95f99d9f7be0056acef0e2e1421fa`.
The real OpenCode shell -> Python package client -> native package job -> dnfast
path passed check, refresh and installation of hello/info, each completed/exit 0.
Install job `81d45f26-039d-4249-a731-139cf03eba47`, RPM transaction
`620a6462-b3e4-7db1-9b63-3caeb1163c85`, actually applied both packages.
`/usr/bin/hello` then printed `Hello, world!` with exit 0. Evidence:
`dnfast-pacman-43b0928-product-{check,refresh,install,hello}.json`.

The updater deliberately refuses any existing state entries, unknown binaries,
symlinks and lock contention. Host tests verified interrupted publication/retry
and original backups. Migration of a populated old state requires its separate
matching-runtime procedure; this test does not establish that path. No DeepSeek
build was started. The app was stopped after these package checks.

The same product APK also passed cancellation of a running repository refresh.
Probe `check-phone-package-cancel.py` observed dnfast PID 22701 with start ticks
10065152, cancelled job `ee954a9d-0a72-4b26-9ffb-50e42b0e1b6b`, and verified the
original process was gone. The stored job reported `cancelled`, exit 255;
PRoot logged signal 3 and tracee termination. A following check retained the
reconciled hello transaction with matching binding, and a fresh repo refresh
completed with exit 0. See `dnfast-pacman-package-cancel.json` and
`dnfast-pacman-after-cancel-{check,refresh}.json`. This is cancellation during
repository work, not interruption during RPM writes. The initial attempt finished
before cancellation and is not counted as a cancellation pass. App stopped afterward.

### Earlier isolated-root check

The corrected launcher and dnfast commit `43b0928d6e8a3d76d6601f9c77e141970755b0a2`
were packaged together in APK SHA256
`8b275dbaafeb00b6819b43ac5efc46b050bf677ea42266f1e83cba781a35f969`.
Clean build, package-input validation and exact installed-APK self-build input
reuse passed. On Pacman UID 10223 / untrusted_app, the separate diagnostic root
`files/dnfast-product-43b0928-v1/linux/rootfs` passed check, repository refresh,
installation of hello/info and verification. All commands exited 0. RPM query
reported hello-2.12.3-1.fc44.aarch64 and info-7.2-9.fc44.aarch64; hello printed
`Hello, world!`. Transaction `2c0c3621-d17b-787f-83b9-24875935440c` was reconciled
with matching binding. Evidence files: `dnfast-pacman-43b0928-isolated-{check,refresh,install,verify}.txt`.

This proves corrected package execution in the app's separate test root. It
does not prove migration of the user's product root or DeepSeek execution.
The app was stopped after verification; user OAuth/workspaces were retained.

## Original failure

2026-09-11. Product deployment is not accepted yet; the six-app DeepSeek campaign remains paused.

Device: Pacman A142, serial `000501423003390`, kernel
`5.15.189-android13-8-gd72397932faa`. The native process ran before PRoot as
UID/EUID/GID 10223, SELinux `untrusted_app:s0:c223,c256,c512,c768`.

The first product check failed opening root ancestor `0`. Passing the app's
canonical root path, while retaining native `O_NOFOLLOW`, advanced execution to
`memfd_create nonexecuting context: Invalid argument`.

A fixed debug-only native probe then confirmed:

| Operation | Actual result |
| --- | --- |
| memfd_create flags 11 | EINVAL 22 |
| memfd_create flags 3 | success, mode 0777, seals 0, app-owned tmpfs |
| add seals 15 | success, final seals 15 |
| write / shrink / grow / add seal / shared writable map | denied, EPERM 1 |
| chmod 0600 | denied, EACCES 13; mode remains 0777 |

Evidence: `evidence/dnfast-pacman-native-memfd-probe.txt`,
`evidence/dnfast-pacman-canonical-check.json`, and earlier root diagnostic files.
The probe exited 0; this is a completed diagnostic, not a passing dnfast transaction.
The app was force-stopped afterward. Existing data and OAuth were preserved.

Correction task: `01a08be2-35c1-7b43-bd66-f2e9fb003393`,
branch `codex/app-context-memfd-compat` from accepted baseline `16c6887`.
Launcher, context and executor plan/manifest contracts must agree. The fallback
must preserve immutable content, identity, locking and signature checks; the
older kernel's lack of execution-bit seals must remain explicit.

The separately retained candidate APK (`bb58f29022c2381574d44a3fc0346d79367c56d9263e0a979797ec796ed91561`)
installed successfully on Lyriq 1. It predates the canonical-root fix and is not
a final dnfast acceptance build. Lyriq 2's same streamed installation was still
pending when this record was written.

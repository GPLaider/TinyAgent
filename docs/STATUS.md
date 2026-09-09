# TinyAgent implementation status

Last inventory: 2026-09-07, Asia/Seoul. Continued: 2026-09-08.
This is a development workspace, not a release candidate.

Current authoritative regression matrix: `REGRESSION-V14.md`. Older sections below
retain bring-up history and do not override that matrix. Latest GUI correction is
v14: default local workspace registration, working empty-home New Session,
unclipped mobile action and touch-tooltip shortcut suppression. Full release
rounds remain 0/3; personal OAuth and clean stock-device acceptance remain open.

Latest installed candidate: v12 on both test phones; Edge 40 runs the actual
phone-produced APK with the existing host development certificate. Harness v6,
system appearance and preserved self-update evidence: `HARNESS-SIGNING-THEME.md`.
The previously tested capabilities-v11 Stock,
Developer and Root fixture installation each passed 3/3 on this same APK.
Actual big-pickle inference inspected Android/Fedora and completed a C-source
failure/edit/rebuild/test loop. Harness v5 corrected unnecessary bootstrap
execution under a no-network task constraint. Details and exact hashes are in
`INTEGRATION-V10-20260908.md` (includes v11). Private OpenAI OAuth remains pending.

## Mandatory stock core (design correction, 2026-09-08)

See `CAPABILITIES.md`. Fedora, the agent and APK builds must run without root or
ADB; Android shell and root administration become optional capabilities. APK
installation is user-confirmed PackageInstaller, authorized ADB, or an explicitly
verified privileged installer. Default startup is now app-UID Fedora/OpenCode.
See `CAPABILITY-INTEGRATION-20260908.md` for three consecutive installation
successes per route, runtime stop/restart tests and their exact APK hashes.
The app-UID Fedora probe and integrated backend passed on Pacman (UID 10225, untrusted_app,
SELinux Enforcing, shell ADB). This is not clean-stock/release acceptance.

## Final acceptance requirement added by the user

The Fedora environment on Edge 40 must rebuild TinyAgent itself. The phone
must obtain the versioned source and dependencies, run the Android build inside
its Fedora workspace, produce an APK with recorded version/hash/signing identity,
and install that APK as an update while preserving settings, sessions and files.
A PC-built APK, hosted build service, mock build or prebuilt APK copy does not
satisfy this requirement. Development/build work may use the 9950X fleet, but
the final self-build evidence must identify phone processes and Fedora paths.
The development self-build and preserved-update path passed on v12. Production
signing and a full clean release rebuild remain open.
See `SELF-BUILD.md`: the actual app-managed Fedora now has verified DNS/HTTPS,
Temurin 17 ARM64, Git, Python, GCC, Make, SDK 36 and working ARM64 AAPT2.
App-UID Fedora on Edge 40 compiled the patched GUI and assembled TinyAgent
first from source 940bc9b. That first APK SHA256 is
`96e9136363797c2e55accf7fdaad532e90e8e3fb7fbee2eab873eb07ddcb9a67`;
its phone-generated debug signature also verified. v12 subsequently used the
shared host development certificate and passed preserved update; production
release signing remains unfinished. Development-tool preparation
now ships in the APK and harness as `/root/.tinyagent/bootstrap/prepare-development.sh`.
The packaged command passed on Edge with existing inputs. It is agent-callable;
there is not yet a separate first-run development-tool progress screen.

Mobile UI work on September 8 is tracked in `MOBILE-UX-20260908.md`.
The revised APK packages the patched official GUI, while retaining the original
phone-local backend. Settings have mobile menu/detail navigation and full-width
forms. Final device acceptance is recorded with each APK hash under `evidence/`.

## Implemented and checked locally

- Native Android connection screen, Dadb self-ADB diagnostics, private app RSA
  identity, UID/device/nonce checks, loopback WebView and Android back/IME state
  handling have been written. Android compilation and lint passed on September 8.
- The actual Java input/URL/UID/path/self-identity policy compiled with JDK 17
  and passed 58 checks. Evidence: `evidence/android-policy-20260908.txt`.
- The upstream collector's stale API-cache trust and stale-success-report defects
  were reproduced before modification: two failing regression tests. Both passed
  after the fix. Evidence: `evidence/collector-before.log` and
  `evidence/collector-after.log`. These use offline synthetic fixtures, not real
  Fedora or OpenCode downloads.
- Signature/checksum parser guards and release-evidence consistency guards passed
  their local self-checks. They do not establish device behavior or provenance of
  an archive that has not been downloaded.
- Source build instructions, fixed harness and dependency notices are recorded.
  Bundled runtime installation and PreRoot backend start/stop are now integrated
  with the native app and tested on device. A debug-signed APK was installed;
  no release APK was produced. Full provider acceptance remains unfinished.

## Confirmed inventory

- Development PC: Ryzen 9 9950X3D, Windows 11 Pro, 16 cores / 32 threads,
  approximately 128 GiB RAM. Debian WSL is installed.
- PC2 LAN SSH did not connect. Its Tailscale SSH endpoint requested additional
  user authentication. No PC2 CPU, checkout or build environment was verified.
- Edge 40 #2: serial `ZY22HZPLL8`, Android 16, `arm64-v8a`, ADB reported
  `uid=0(root)`, SELinux context `u:r:su:s0`. TinyAgent/Termux not installed at
  inventory time. `su` was absent; root ADB and a `su` binary are separate facts.
- Edge 40 #1: serial `ZY22J58799`, Android 16, ADB reported `uid=2000(shell)`;
  TinyAgent/Termux not installed at inventory time.
- The selected initial test target is #2. The separate `.debug` app was installed
  and its Korean setup UI rendered. No flash, reset or rootfs provisioning occurred.

## Source provenance

Official OpenCode source was checked out from
https://github.com/anomalyco/opencode at release `v1.18.29`, commit
`16747470f976aca3d362ad730bcd3fe82ecc2c9a`, under
`D:\TinyAgent-work\upstream\opencode`. Its working tree was clean when
rechecked on September 8.

The GUI uses SolidJS/Vite. The release build embeds the GUI in the Linux ARM64
backend. The v1 `/global/health`, provider/auth/config, session and SSE APIs are
the intended reuse path. MIT copyright and permission notices must accompany
redistribution. Bun/JavaScriptCore and other included dependencies need their
own notices and corresponding source/rebuild records.

PreRoot is a TinyAgent-owned implementation, not an external prerequisite.
Its initial source is `preroot/`, using the measured Android namespace/chroot
mechanism. Execution provider IDs are `android-self-adb` and `fedora-preroot`;
model provider IDs remain those supplied by OpenCode. The selected installation
layout and current implementation limits are in `preroot/README.md`.

## Current constraints

Earlier sandbox-related network/ADB limitations were cleared on September 8.
The canonical source is `D:\TinyAgent-work\tinyagent`; the old workspace path is
a junction. D: also holds build temporary files to avoid Windows Java socket
and non-ASCII Gradle path failures. Build and lint now work.

The target adbd listens only on `100.79.65.42:5555`, not `127.0.0.1:5555`.
The initial app failed with ECONNREFUSED. Local-interface address discovery was
added; its real UI regression runner is `scripts/check-device-adb.py`.

No user provider credentials have been copied or used. The public OpenCode
provider completed a real response and Bash tool call in the diagnostic Fedora
environment; the exact scope is recorded below. Fedora's signed checksum was verified against the pinned
Fedora 44 public key, then the Fedora and OpenCode ARM64 archives were downloaded
and hash-verified. The manifest is `D:\TinyAgent-work\artifacts\upstream-manifest.json`.
A separate native-chroot compatibility rootfs was prepared on the phone at
`/data/local/tmp/tinyagent-compat-20260908`. Fedora Bash and OpenCode 1.18.29 ran.
Without `/proc` and `/dev`, Bun crashed during initialization; adding those in
a separate mount namespace resolved the version probe. This is not PreRoot.
The authenticated diagnostic backend runs with cwd `/workspace`, and the
TinyAgent WebView displayed its Korean GUI. `phone-backend-health.txt` records
the actual PID/root/cwd and unauthenticated 401/authenticated healthy response.
Its launch is currently held by a host ADB command, not an app runtime service.
Using the phone's measured DNS addresses, Fedora HTTPS returned 200 and microdnf
installed Git 2.55.0, Python 3.14.7, Make and GCC 16.2.1. The C development smoke
test reproduced an assertion failure (40 instead of 42), edited the real file,
rebuilt it and passed. Android serial/device/UID data was processed in Fedora
and read back from Android. `phone-development-smoke.log` is the evidence.
These are operator-driven environment checks, not agent/provider journey passes.

## Acceptance status

All seven complete device journeys remain **unpassed**. Consecutive accepted
release rounds: **0 / 3**. A host unit check is never substituted for a device
journey or an actual provider request.

The fixed harness exists as a source file, but startup/resume injection and its
example commands in both phone environments remain unverified. The environment
snapshot file must be generated from runtime measurements; none is fabricated.

The upstream mobile home route lost scroll position: the production-browser
test reproduced 735px becoming 0px after entering a session and going back.
Persisting/restoring the home position passed at 735px before and after.
The original three production navigation benchmarks passed two and failed the
review-body visibility case. After the fix plus new mobile test, three passed
and the same existing review-body case failed. `home-regression.log` records it.
App and E2E typechecks passed after restoring Git's intended Windows symlinks.
The patch is `patches/opencode-mobile-home-scroll.patch`. It is tested with
synthetic API fixtures in a production browser build, and is not yet bundled
into the phone's original upstream binary. Korean IME remains unverified.

PreRoot 0.1.0 now executes against the existing diagnostic Fedora root. Nine
device checks passed: measured identity, Fedora UID, cwd, OpenCode version,
child failure status, missing cwd failure, unsupported permission refusal,
invalid action refusal and no global mount leakage. Evidence:
`evidence/preroot-entrypoint.json`; rerun with `scripts/check-preroot.py`.
This is execution-entrypoint validation, not bootstrap or lifecycle acceptance.
Runtime provisioning, persistent data mounts and app-triggered backend lifecycle
are now implemented and tested as described below. Complete lifecycle recovery,
model-provider configuration and the complete journeys remain implementation work.
No external PreRoot source or user choice of execution-provider names is needed.

## September 8 managed runtime device cycle

- Current tested APK SHA256:
  `d3f9feed195dc76a17e6d19cd67dd7de6f18cb3c4aa31e1a79972e41ca9c77c7`.
  It uses the existing development certificate, version 0.1.0-dev / 1.
- First app installation attempt exposed AGP's transparent `.gz` asset expansion:
  the installer could not find the packaged archive. Staging as `.gz.bin` preserves
  original compressed bytes. Build now checks hashes inside the final APK.
- `setup-first-install-fixed-01` and `setup-reuse-fixed-01` passed actual button
  installation/version probing. The persistent workspace marker survived reuse.
- `setup-managed-backend-01` passed app-owned setup and detached backend launch.
  `managed-auth-ui-02` passed cold app restart and native HTTP authentication into
  the actual Korean GUI, without entering a server password.
- `managed-app-stop-02` verified the native stop button, disappearance of the
  recorded backend PID and byte-identical workspace marker. App restart checks
  are `managed-app-restart-01` and `managed-app-restart-02`.
- `managed-backend-cycle-1.txt` through `-3.txt` record three consecutive shell
  manager stop/start/health cycles: PPid 1, correct root/cwd, unauthenticated 401,
  authenticated healthy 1.18.29, unchanged marker and no global rootfs mounts.
  These are component cycles, not the three required full release rounds.
- Actual backend config returned `permission: {"*":"allow"}` when started through
  the app with unrestricted root selected. Turning root off does not yet stop an
  already running backend automatically; this must be fixed before release.
- `public-provider-smoke.txt`: diagnostic backend used
  `opencode/nemotron-3.5-lightning-free`, ran `pwd; cat /etc/fedora-release`, exited
  0 and returned `TINYAGENT_MODEL_OK`. Reported model cost was 0. The initial wait
  was an external-directory permission prompt; the exact read was allowed once
  through the API. This is not acceptance of the mobile provider settings flow.

The Android foreground dataSync service performs preparation/control and then
stops. OpenCode stays detached under Android init in its own mount namespace.
The manager validates PID, process start ticks and boot ID before signalling its
process group. Jobs that deliberately detach into other process groups are not
yet covered by full runtime shutdown verification.

Remaining: interrupted-setup recovery, automatic permission revocation, dynamic
DNS/network recovery and development packages in the new production root,
Android tools from the agent, measured harness injection, provider settings/key
refresh/custom endpoint tests, bundled mobile GUI patch, Korean IME and all
seven complete release journeys. Overall release rounds remain **0 / 3**.

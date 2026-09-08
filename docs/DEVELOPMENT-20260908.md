# Development checkpoint — September 8

Latest app-managed runtime APK:
`D:\TinyAgent-work\artifacts\tinyagent-0.1.0-dev-managed.apk`, SHA256
`d3f9feed195dc76a17e6d19cd67dd7de6f18cb3c4aa31e1a79972e41ca9c77c7`.
The earlier APK and diagnostic steps below are historical baselines. Current
component acceptance and remaining release work are in `STATUS.md`.
Stage runtime inputs with `scripts/stage-runtime-assets.py D:/TinyAgent-work/artifacts`
before building. The build script now verifies both archives inside the APK.

Canonical project: `D:\TinyAgent-work\tinyagent`.
Upstream: `D:\TinyAgent-work\upstream\opencode`, tag `v1.18.29`, commit
`16747470f976aca3d362ad730bcd3fe82ecc2c9a`.
The original workspace's TinyAgent path is a junction to this project.

## Android

Run `scripts/build-android.ps1` with JDK 17 and SDK 36. It applies the Windows
Java socket-directory workaround and runs assembleDebug plus lintDebug.
The checked development APK is
`D:\TinyAgent-work\artifacts\tinyagent-0.1.0-dev-selfadb.apk`, SHA256
`48c82c56969546238fecaff3addbbbdf106d55255a854c361f5b76674010f9c4`.
It uses the debug certificate documented in `evidence/APK-GATE.md`.
Install only after matching the selected device serial and APK certificate.

## Upstream browser development

Use `scripts/prepare-bun.py` to obtain verified Bun 1.3.14 under
`D:\TinyAgent-work\tools`. Use a Git checkout with native symlinks enabled
(`git -c core.symlinks=true clone ...`). Plain-text symlink placeholders break
`custom-elements.d.ts` and public assets on Windows.

Add the Bun directory to PATH, set BUN_INSTALL_CACHE_DIR to a D: directory,
then run `bun install --frozen-lockfile` at the upstream repository root.
Apply `patches/opencode-mobile-home-scroll.patch` to the pinned source.
From `packages/app`, run `bun typecheck`, `bun typecheck:e2e` and the production
benchmark command below with PLAYWRIGHT_BROWSERS_PATH on D: and
OPENCODE_PERFORMANCE=1:

    bun x playwright test --config e2e/performance/playwright.config.ts home-tab-navigation-benchmark.spec.ts

The current known baseline failure is the review panel visibility assertion.
The new mobile test dismisses the real Tabs announcement, uses a scrollable
session list, opens a session and checks its browser-back scroll restoration.
These fixture-based checks are not phone/provider acceptance.

## Phone compatibility probe

`collect_upstream.py --output D:/TinyAgent-work/artifacts` verifies the Fedora
signature and archive digests. `prepare-fedora.py` verifies OCI descriptors,
ARM64 identity, the single gzip layer and uncompressed diff ID. It rejects
unsafe extraction members and stages the original layer without extracting
Linux filesystem links on Windows.

The probe root belongs only to TinyAgent's diagnosis, not a completed runtime:
`/data/local/tmp/tinyagent-compat-20260908` on `EDGE40_ROOT_SERIAL`.
The matching scripts are in `/data/local/tmp/tinyagent-stage-20260908`.
`probe-fedora-android.sh` performs the first extraction and refuses an existing
root. Do not run it again over the populated root.

Start the temporary server with these literal Android argv:

    unshare -m /system/bin/sh /data/local/tmp/tinyagent-stage-20260908/probe-fedora-namespace.sh serve

The script makes mount propagation one-way before mounting proc/dev, validates
namespace separation, creates a phone-local private diagnostic password, and
runs OpenCode on 127.0.0.1:4096 with cwd /workspace. It does not expose the password
in logs. `check-phone-backend.sh` verifies PID/root/cwd, unauthenticated 401 and
authenticated health. The app's native HTTP authentication dialog successfully
opened the actual Korean GUI; see `evidence/backend-first-webview/screen.png`.

This foreground ADB-held process is not an Android foreground service. Before
stopping it, re-identify its PID and `/proc/PID/root`; terminate only that PID.
Its namespace mounts disappear after all processes in that namespace exit.
No system partition, global SELinux policy or Android persistent USB setting
was modified. The new TinyAgent-owned PreRoot source is `preroot/`; its
entrypoint checks reuse this diagnostic root without moving or replacing it.
Run `scripts/check-preroot.py` for real-device execution and failure-path checks.
Provider credentials have not been used; model acceptance remains unpassed.

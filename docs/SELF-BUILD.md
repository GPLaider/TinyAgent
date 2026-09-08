# Phone-local TinyAgent self-build acceptance

The final target is the app-managed Fedora on Edge 40, serial `EDGE40_ROOT_SERIAL`.
Source compilation, GUI asset generation, Android resource compilation, DEX
generation and APK signing must run on the phone. Record the source revision,
tool versions, working directory, process architecture, exit status and APK hash.
Install that output as an update and verify settings, sessions and workspace files.
Copying a PC-built APK does not pass this requirement.

## Current evidence, 2026-09-08

Latest phone-produced APK: source `24666a4d1c625ecbd140648e333b7a079e51d944`,
native/assets rebuild 2m39s, with the previously phone-compiled GUI reused.
SHA256 `abd22ba4fb37a0150138df2b3b2c7e85cbeebd4cd16a725831391e63d3b607a0`.
All packaged checks passed. Its signer matches the host development stream;
this exact output updated Edge 40 without uninstalling. Existing backend
credential, model session and C source survived, and the C test passed again.
See `HARNESS-SIGNING-THEME.md`. Production signing remains unset.

Previous phone-produced APK (harness v5): source
`11e81854c40f78ee3cef75815f498e05427cb37e`, native/assets rebuild 1m31s,
all packaged checks passed, phone debug v2 signature verified. Output:
`D:/TinyAgent-work/artifacts/tinyagent-phone-11e8185-debug.apk`, SHA256
`c209e9b39f3f114fd7daf7acdcb7ada0e4b9a1d9b2bc63ffc4cafc7e549cc0b0`.
The unchanged GUI is from the full phone build below. The installed v11 on
both phones remains host-debug-signed; that signer differs from this output.

The second complete build used `d3d6392a4f3e191640ceac42407f92d8720260a3`
in `/workspace/tinyagent-self-build-940bc9b`. App-UID Fedora compiled the GUI in
5m42s, then Gradle assembled the APK in 2m58s (37 tasks, 7 executed). All packaged
bootstrap, native, notices, GUI and runtime checks passed; runner exit was 0.
Evidence: `edge40-self-build-d3d6392.json` and its process/battery logs.

Output: `D:/TinyAgent-work/artifacts/tinyagent-phone-d3d6392-debug.apk`.
SHA256: `c01db18eb5f5e41731f0738159f0b749f6db635137558a67124c6f1a9e914a29`.
APK v2 signature verifies with the same phone debug certificate listed below.
This still cannot update the host-signed installed APK. No signing key moved.

The first retry at 436c74d failed while downloading the GPL notice from GNU
(connection reset). The corrected collector reuses the complete versioned
notice and verifies its pinned hash. The next full build passed.
The SDK now includes ARM64 platform-tools; its earlier license warning is gone.
The root tsconfig warning remains and is not claimed fixed.

The APK now bundles `/root/.tinyagent/bootstrap/prepare-development.sh`, exposed
by harness v4. That exact packaged script passed through the real backend.
The following records explain the earlier failures and first successful build.

The following root-runtime inventory is historical. Current work runs in
`fedora-local`, Android application UID 10151, on the same Edge 40. The new source
checkout is `/workspace/tinyagent-self-build-940bc9b`, commit
`940bc9b22bbd4707a09b76a3eca5424abb403f3f`. See
`evidence/edge40-stock-source-clone.json` for the actual backend shell clone.
Package setup, Java 17, Git, Python, ARM64 AAPT2 and Android SDK 36 setup passed
there. Runtime DNS now refreshes from Android LinkProperties; development-tool
preparation remains a manually invoked script.

`scripts/development-loop-fedora.sh` reproduced a failing C test (exit 2), edited
the real source from `6 * 6` to `6 * 7`, rebuilt with GCC and passed the same test
(exit 0), with UID, hashes and diff in `edge40-stock-development-loop.json`.
This exercised the real OpenCode shell API without model inference.

The first full self-build failed during Bun hardlink installation (`EPERM`).
`--backend copyfile` completed dependency installation, but Vite then failed.
Diagnostics found an absent `vite-plugin-solid/package.json`. Reinstalling from
the same cache still produced empty package directories. The cache had PRoot
L2S links left by the original hardlink attempt. A separate cache plus copyfile
and an explicitly created node_modules directory passed a minimal Vite/Node
execution check (`edge40-stock-bun-copy-clean-probe.json`). Reusing symlinks for
the full isolated monorepo instead failed on transitive Rollup resolution.
The full clean-cache/copyfile retry succeeded: Vite transformed 2560 modules and
built in 5m22s, staging 952 GUI files (36058045 bytes). Gradle 8.13 completed all
36 Android tasks in 6m39s. Native PRoot, GUI and original compressed-runtime hash
checks passed inside Fedora. Both runner exit markers were zero. Evidence:
`edge40-stock-self-build-copy-clean-cache.json`.

Phone-built APK SHA256:
`96e9136363797c2e55accf7fdaad532e90e8e3fb7fbee2eab873eb07ddcb9a67`.
Size: 128295973 bytes. Source: 940bc9b22bbd4707a09b76a3eca5424abb403f3f.
Phone apksigner verified APK Signature Scheme v2, with the freshly generated
phone debug certificate SHA256
`31e6ce48aa6d84279c5e9f6eee443091a9816553f63122191f6d022106568cfa`.
See `edge40-stock-self-build-signature.json`. This key differs from the host
debug signer, so the APK cannot update the currently installed host-signed app.
No private signing key was copied.

A 2285736-byte lossless transfer delta exported the phone-produced bytes; host
reconstruction verified the same full APK hash. Local output:
`D:/TinyAgent-work/artifacts/tinyagent-phone-940bc9b-debug.apk`.
Export is a transport step, separate from the recorded phone compilation.
The versioned full runner now uses the clean-cache strategy and Node 22. The successful older attempt
logged a missing-root-tsconfig warning and a missing platform-tools/license
warning; neither prevented APK assembly. SDK completeness still needs work.

`evidence/self-build-inventory-before.log` identifies Fedora 44/aarch64 inside
`fedora-preroot`, `/workspace`, unrestricted root and roughly 220 GiB free.
It reproduced missing DNS, Java, Git, Python, Make, GCC and AAPT2.

`scripts/prepare-self-build.sh` runs inside the same app-managed Fedora. It takes
DNS addresses measured from Android's current LinkProperties, writes resolv.conf,
checks HTTPS and installs development tools through Fedora's signed repositories.
This historical test invoked the script manually. Current app startup prepares
the core, refreshes DNS from Android, and provides the development bootstrap to
the agent. Full network-transition acceptance is still unfinished.

The first installation failed because Fedora 44 has no java-21-openjdk-devel.
The retry used official Temurin 17 ARM64, pinned to archive SHA256
`457b57af8f9c93ec39080bb8c764f559dc8c89a6da1a39d718a400b7890d3e41`.
Metadata source: [Adoptium API](https://api.adoptium.net/v3/assets/latest/17/hotspot?architecture=aarch64&image_type=jdk&os=linux&vendor=eclipse).
`evidence/self-build-base-tools.log` records successful installation, HTTPS 200,
archive checksum verification, Java/javac 17.0.20.1, Git 2.55.0 and Python 3.14.7.
JDK location inside Fedora: `/opt/tinyagent-build/jdk-17.0.20.1+1`.

The versioned source is now checked out inside Fedora at
`/workspace/tinyagent-self-build-2addbe3`, revision
`2addbe37840b86437626c74d2d284a866ea525b8`. Its transferred Git bundle SHA256
was verified on both host and phone:
`709975bf5f63113fa6c0e2e9ad7d1ae0158f7f121359e2e4eb403c547159ca9b`.
The source's existing wrapper downloaded its checksum-pinned Gradle 8.13 and
ran successfully with Java 17 on the actual Android aarch64 kernel. See
`evidence/self-build-gradle-version.log`. This verifies Gradle startup only.
The real `:app:assembleDebug` attempt then failed with `SDK location not found`;
see `evidence/self-build-apk-before.log`. `build-android-fedora.sh` keeps build
arguments in the owning Bash script after a host argument-parsing failure,
limits Gradle to two workers and a 1536 MiB heap, and records revision/path/PID.

## Remaining acceptance gates

- Verify clean-stock first-time SDK preparation and remaining dependency/source
  provenance. ARM64 SDK, GUI and APK compilation already passed on Edge.
- Establish a signing identity for phone-produced updates. The installed debug
  APK has a host debug signer; a fresh phone debug key cannot update it. Do not
  copy a personal or release private key to the phone implicitly.
- Install the phone-built APK and verify preserved configuration, sessions,
  workspace files, backend recovery and all seven release routes.

A debug TinyAgent APK has now been built and signature-verified inside app-UID
Fedora. Release signing, installation of that output as a state-preserving
update and the complete release journey suite have not passed yet.

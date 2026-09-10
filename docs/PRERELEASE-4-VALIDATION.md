# Preview 4 validation ledger — in progress

Candidate APK: `TinyAgent-0.1.0-preview.4-arm64.apk`.
SHA256: `b7eb6d1f860fd3f8a0ab371a710013cc44d3483e0e6a71bd1a57315e80baaf71`.
Version: code 3 / 0.1.0-preview.4.
Development certificate: `a3ef78ae0bfdfc30307e3448e138eca29adf39d966f89af116bbce151abc1ed2`.
Host build, APK signature, packaged harness/bootstrap/952 GUI files/native components/runtime archives passed.
Exact candidate device acceptance is pending. Do not substitute older APK results.

## Pacman functional builds on the preceding internal APK

Device 000501423003390, Nothing A142, Stock TinyAgent app UID 10223, Android SELinux Enforcing.
Internal APK SHA256 `fe690f6e884a7bd152703ffc2cd3d81a688e62bebc698ddb5c915af439cd19f3`.
Host ADB shell UID 2000 stages and observes; actual Fedora builds execute through the local OpenCode shell API.
Fresh app environment preparation passed. OAuth was not moved from Lyriq1.

- AntennaPod d05a58b: build passed, 1238.233 seconds; APK 7a5fac09f0afd30295d2dfc15d4b9f92625f5df0b57ddb392a752ca10c157fb5.
  TinyAgent Stock PackageInstaller approval, matching installed APK hash and visible Home screen passed.
- Termux 3b66f87: build passed, 606.669 seconds; ARM64 APK ea8f8259ab523029f92bf12cf189f879c3b9070806d336dbf98dee42150b798e.
  TinyAgent Stock approval install, bootstrap completion and interactive uname -m -> aarch64 passed.
  Other ABI APKs were built, not run. This is the app build, not the full termux-packages ecosystem.
- Tailscale: first build failed because gomobile could not find plain go. Runner now uses the same pinned Go as tool/go; retry queued.
- Organic Maps: ARM64 Clang/CMake configuration passed; native build in progress.
- VLC and AppFlowy: queued; no successful APK claimed.

Builds share one development root and a serialized build slot. Their times are not fresh dnf5/dnfast provisioning benchmarks.
max_single_child_rss_kib excludes descendant daemons; it is not a process-tree peak RSS measurement.

## Failures retained

- Native dependency inventory incorrectly queried zlib-devel as a literal installed package. Changed to rpm --whatprovides; installed provider is zlib-ng-compat-devel.
- Fedora rustup RPM provides rustup-init. Added explicit noninteractive initialization, then Rust 1.85.0 and aarch64-linux-android target succeeded.
- Earlier dnf5 transaction failed while installing corelist and libtic.so. Identical cached RPMs succeeded on a targeted normal retry.
  Root cause remains unproven. No SELinux or signature verification bypass was used. This is not evidence of a dnfast defect.

## Remaining release acceptance

Final-candidate update/data preservation, model/tool smoke, mobile interactions and three consecutive recovery rounds.
Finish the remaining app builds/debugging, collect installed artifact behavior, and report unsupported toolchains honestly.
Long Doze, credential-lock behavior, provider/token-refresh matrix, controlled fresh-root dnf5/dnfast comparison and full seven-journey release gate remain open.
Published Preview3 remains unchanged while this candidate is under test.

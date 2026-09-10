# Preview 4 validation ledger — in progress

Candidate APK: `TinyAgent-0.1.0-preview.4-arm64.apk`.
SHA256: `ee39113fad165b1e7b3a8548c2886739c143bcbdbb7f596e4aaf94b3cef7e606`.
Version: code 3 / 0.1.0-preview.4.
Development certificate: `a3ef78ae0bfdfc30307e3448e138eca29adf39d966f89af116bbce151abc1ed2`.
Host build, lint (0 errors, 56 warnings), APK signature, packaged harness/bootstrap/952 GUI files/native components/runtime archives passed.
Lyriq2 ZY22HZPLL8: exact candidate installed as an update. Existing 100 listed sessions (plus individually fetched older IDs), backend credential fingerprint and provider connection preserved.
Actual opencode/big-pickle model response and completed bash tool calls passed (42.657 seconds); this does not verify OpenAI OAuth.
Real WebView touch injection passed three consecutive rounds: long press, multi-select, bulk delete/undo, swipe delete/undo for sessions and projects; backend sessions preserved.
Debug dnfast result-contract, already-installed no-op and timeout/actual process exit passed on this exact APK under app UID10151 / untrusted_app / Enforcing.
Exact candidate passed three consecutive 120-second screen-off rounds with real Fedora commands and restored sessions. Service stop removed backend processes and released the app CPU lock; restart reacquired it. The test now waits for backend health after asynchronous restart before creating sessions.

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
- Tailscale: fixed plain go lookup; next failure was pinned gomobile rejecting Linux arm64 hosts. A separate local module copy now selects linux-arm64; original module cache remains untouched. ARM regression check/build retry queued.
- Organic Maps: native C++ and APK packaging completed in 2185.293 seconds, but final permission verification invoked x86 aapt2. Its checker now honors the ARM override; full task retry queued, no successful build claimed yet.
- VLC: first attempt stopped because upstream git am required committer identity. Pinned patches were applied with build-process identity; normal upstream checks remain enabled. Retry queued.
- AppFlowy: Rust tooling compilation in progress; no successful APK claimed.

Builds share one development root and a serialized build slot. Their times are not fresh dnf5/dnfast provisioning benchmarks.
max_single_child_rss_kib excludes descendant daemons; it is not a process-tree peak RSS measurement.

## Failures retained

- First candidate b7eb6d1f failed lint: Path.of requires API 34, while minSdk is 30. Replaced the sole caller with Paths.get. Build/lint passed on ee39113f; the rejected candidate was not installed.
- Native dependency inventory incorrectly queried zlib-devel as a literal installed package. Changed to rpm --whatprovides; installed provider is zlib-ng-compat-devel.
- Fedora rustup RPM provides rustup-init. Added explicit noninteractive initialization, then Rust 1.85.0 and aarch64-linux-android target succeeded.
- Earlier dnf5 transaction failed while installing corelist and libtic.so. Identical cached RPMs succeeded on a targeted normal retry.
  Root cause remains unproven. No SELinux or signature verification bypass was used. This is not evidence of a dnfast defect.

## Remaining release acceptance

Final-candidate update/data preservation, model/tool smoke, mobile interactions and three consecutive recovery rounds.
Finish the remaining app builds/debugging, collect installed artifact behavior, and report unsupported toolchains honestly.
Long Doze, credential-lock behavior, provider/token-refresh matrix, controlled fresh-root dnf5/dnfast comparison and full seven-journey release gate remain open.
Published Preview3 remains unchanged while this candidate is under test.

The preceding fe690f6e internal APK passed three 600-second screen-off rounds on Lyriq2, including real Fedora commands while off and preserved sessions. This is not credential-lock, prolonged Doze, or Preview4 acceptance.
The self-build recipe now includes both debug native executables from retained source. Host rebuilding reproduced the FD seed hash c5711e31; the ARM phone build is still queued.

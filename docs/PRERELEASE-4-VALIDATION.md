# Preview 4 validation ledger — in progress

## Current state, 2026-09-10

The records below cover several APKs and earlier attempts; they must not be
combined into a three-round pass for the newest candidate.

- Lyriq1 now has `TinyAgent-gui-prod-channel.apk`, SHA256
  `5c9f27b0579e0566606f2017bb4d85f00925f3667e62f21004b48c3b54c150af`.
  See GUI-PRODUCTION-CHANNEL.md for update preservation and visible evidence.
- Patched PRoot parent-death and automatic stopped-runtime state recovery:
  see PROOT-EXITKILL-VALIDATION.md and STARTUP-RECOVERY-VALIDATION.md.
- Six Pacman builds: four APKs produced (AntennaPod, Termux, Organic Maps,
  Tailscale); first three installed and shown. Tailscale launch remains pending.
  Current VLC session `ses_f7602a040ffexZctrjigdpFcaW` is running under app
  UID10223, with live make/cmake and advancing configure output. No VLC APK yet.
  AppFlowy and current-source TinyAgent self-build remain incomplete; older
  killed/queued attempts are not active work.
- Screen-off testing has been reassigned by the owner to Lyriq2. Lyriq1's
  latest readback confirmed the isolated shell exited 0, but the interrupted
  observation does not establish a complete screen-off acceptance interval.
- These shared-workspace builds do not establish dnfast/dnf5 comparative
  performance. Fresh controlled provisioning measurements remain pending.

## Earlier Preview 4 candidate evidence

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
- Organic Maps 958ddb7: first attempt stopped at the permission checker after 2185.293 seconds because it invoked x86 aapt2. The checker now honors the ARM override without skipping permission validation. Retry passed in 269.969 seconds. APK SHA256 3f4d858109c37f45ace49c6c94ce0e7acb8a52e6292e93e0b82e5f5c45f3a14f, 116583558 bytes. Stock approval installation, installed hash and visible world map passed. Evidence: evidence/pacman-organic-maps-build-1789005962326825763/. GPS/navigation was not tested.
- VLC: pinned patches passed with process-local Git identity. The next attempt failed because bzip2 was missing; it is now included in native prerequisites. Retry session ses_f76e0ba9effe26QHKFmYGYSggA is queued; no APK success claimed.
- AppFlowy: initial native build failed because OpenSSL used a PRoot L2S Perl path in a shell command. Explicit PERL=/usr/bin/perl passed the exact OpenSSL Configure reproduction. Retry ses_f76e5fba5ffemXnquE0SlPndOn has progressed into AppFlowy's Rust modules; no successful APK claimed.

Builds share one development root and a serialized build slot. Their times are not fresh dnf5/dnfast provisioning benchmarks.
max_single_child_rss_kib excludes descendant daemons; it is not a process-tree peak RSS measurement.

## Failures retained

Stock Android-to-Fedora exchange passed three consecutive executions on Preview4 / Lyriq2. The live harness socket was used for GET /inspect/stock; Android execution UID and the actual Fedora process Android UID both measured 10151. Each run saved the Android response, processed it in Fedora, re-read the saved JSON and recorded hashes. Evidence: evidence/preview4-stock-exchange-{1,2,3}.json. This is direct shell-API integration evidence, not model-led acceptance or proof of Developer/Root modes. The exchange test now has explicit stock/developer/root options with mode-specific authority assertions; the previous Root default is preserved.

Exact Preview4 media acceptance: actual opencode/big-pickle response in session ses_f76a1ea74ffeTD13ykNzGfi26r rendered workspace inline-code links. Native touches opened PNG 보기/저장/공유 and MP4 재생/저장/공유 menus. The PNG decoded visibly; the MP4 showed a decoded frame and playback controls. Android share sheet displayed sample.mp4 (no recipient selected). SAF export to /sdcard/Download/sample.mp4 matched source SHA256 baedfb5d1c1d0830e5500995e327911412e7478041d77d221bf3ff68c0d10d12. Evidence: evidence/preview4-media-acceptance.json and its screenshots. This is one PNG/MP4 sample, not a codec matrix or three rounds.

- First candidate b7eb6d1f failed lint: Path.of requires API 34, while minSdk is 30. Replaced the sole caller with Paths.get. Build/lint passed on ee39113f; the rejected candidate was not installed.
- Native dependency inventory incorrectly queried zlib-devel as a literal installed package. Changed to rpm --whatprovides; installed provider is zlib-ng-compat-devel.
- Fedora rustup RPM provides rustup-init. Added explicit noninteractive initialization, then Rust 1.85.0 and aarch64-linux-android target succeeded.
- Earlier dnf5 transaction failed while installing corelist and libtic.so. Identical cached RPMs succeeded on a targeted normal retry.
  Root cause remains unproven. No SELinux or signature verification bypass was used. This is not evidence of a dnfast defect.

## Remaining release acceptance

Pacman Tailscale build completed: pinned source ee64696ee308f5e72853b8e4af817b49fab860c1,
make apk including Gradle test and assembleDebug exited 0 in 2283.265 seconds.
Collected APK is 151005739 bytes, SHA256 ac68c5b0a1b5e9328c8934cc5a265ae47ebe72aec3edf1dc086241065443fd35.
Evidence: evidence/pacman-tailscale-android-build-1789014833905597292/.
This is the fourth of six APK builds; Tailscale installation/launch is still pending.
VLC has acquired the build slot and is compiling native build tools. AppFlowy and
the separate complete TinyAgent self-build are not counted as passed.

Video UI: b05bc77d and 738a19ff retained controller-placement defects.
708e8ffc moved video to a normal activity and fixed spatial placement, but its
close/reopen test found a first-touch close failure while floating controls were
present. An embedded Button/SeekBar implementation is now under test; no final
three-round media acceptance is claimed. See evidence/lyriq1-video-activity-708e8ffc.json.

Lyriq1 screen-off observation during third Luna development session ses_f7662662bffeLJbDM3NWSzN40L: approximately 144 seconds with mWakefulness=Dozing and TinyAgent:LocalRuntime partial wake lock held by app UID 10042. App/PRoot/backend processes survived. After wake, deviceLocked=1 and CDP Runtime.evaluate timed out; user credential unlock is required to compare model tool timestamps and final results. This is process/power evidence only, not a completed screen-off model-work or three-round acceptance claim. Evidence: evidence/lyriq1-luna-screenoff.json.

On the same d5811e1a APK, model-led Python repair rounds ses_f766b3658ffeNOjH7Q5wjHqFU9 and ses_f7665db0effexK8HSgTJRcuP0M both passed independent transcript/file validation. Round 2 used add(0,7) for the zero case, so all three initial tests failed; the unchanged suite passed after the source fix. Evidence parser now accepts actual nonzero unittest failure counts and colon/equal exit-code labels instead of requiring a particular model's formatting. Both cases still require real failed tests, unchanged test source, successful retest and compile. Three consecutive rounds and the wider seven-journey gate remain pending.

Tailscale's first host regression output said no tests to run: tinyagent_arm_test.go was excluded by Go's ARM filename suffix on ARM64. Renamed it to tinyagent_host_test.go and require the exact test pass event from go test -json. The corrected test actually ran and passed on Pacman (evidence/pacman-gomobile-real-test.json, session ses_f7663f534ffeTAR2XKFNLLKTvw). Production Go sources were not modified during this verification; the existing gomobile/AAR build remains in progress. This test establishes only Linux ARM64 host directory selection, not APK completion.

Latest internal d5811e1accdb174c5a50450c79931374fd1405e1fe5efd627f193f33113d3863 was installed on Lyriq1 with its existing development signer. ZIP payload reuse transferred 4399787 bytes and reconstructed the exact 141773527-byte signed APK on the device; installed hash matched. All 25 prior sessions, connected providers and dark setting survived. The existing Luna result.json link now exposes Open/Save/Share; native Open displayed the actual result content. Provider settings now show connected OpenAI without the misleading Custom badge, while backend OpenAI/Luna availability remains true. Evidence: evidence/lyriq1-json-provider-update.json and referenced screenshots/snapshots. Previous candidate evidence is not automatically a full gate pass for this hash.

Lyriq1 ade8840c model-led development fixture passed once in ses_f7673ee2cffe77J5KF15vuAONf using existing OpenAI OAuth gpt-5.6-luna. Actual tests failed with two failures/exit 1, calculator.py changed from subtraction to addition, the unchanged three-test suite passed/exit 0, and py_compile completed/exit 0. Independently fetched files and tool transcript passed scripts/check-luna-development-evidence.py. Android process observer saw app/backend under u0_a42; guest id=0 is PRoot emulation. The final model-created result.json link opened the native artifact menu, but JSON had only Save/Share. Added application/json and +json to existing bounded text preview. That native UI fix still requires rebuilding and touch verification. This is one small Python fixture, not the full three-round seven-journey release gate.

Provider UI audit on Lyriq1 ade8840c: Home > Settings > Providers opens the existing OpenCode provider panel and shows OpenAI connected. Read-only backend audit confirms OpenAI and Luna availability; no disconnect or credential edit was performed. Screenshot evidence/lyriq1-provider-ade8840c.png captures a misleading Custom badge. Backend provider.ts uses source=custom for both built-in auth plugin loaders and other custom loaders; this does not prove a user-defined endpoint. Both settings panels now omit that ambiguous source badge, retaining the explicit configured-custom-provider badge. Typecheck, production GUI build and reverse source-patch check passed. This subsequent source change is not yet installed; OAuth refresh/custom endpoint mutation tests remain pending.

Composer refinement candidate ade8840c33a84335add8f5dc211ad9eb662a6ba4179f622431a7ac5fa78cea84 (141773528 bytes, same development signer a3ef78ae) was installed on Lyriq1 ZY22J58799 with install -r. Device APK hash matched. All 23 preceding session IDs, connected OpenAI/OpenCode and dark setting survived. The prior UI failed the compact-control check; the new native details control passed three touch expand/collapse rounds with unchanged selected mode and 44 CSS px touch target. Collapsed height is 53.6 CSS px. Existing OAuth gpt-5.6-luna session ses_f76785472ffekIjmZKpuzCfcsz completed pwd, uname -m and cat /etc/fedora-release, all exit 0. Evidence: evidence/lyriq1-composer-update.json, referenced snapshots/touch report/model transcript and screenshot. This hash is a new internal candidate, not the ee39113f draft release asset; previous whole-device acceptance is not automatically transferred.

AppFlowy Gradle started downloading its hard-coded NDK 24 despite ANDROID_NDK_HOME pointing to the prepared ARM NDK. The retained next-run recipe sets Gradle ndkVersion from that NDK's source.properties, ndkPath explicitly, and cmake.dir=/usr. Python syntax passed; the running build was not changed, and this correction still needs actual retry validation. This is a build toolchain integration issue, not a demonstrated dnfast defect.

Lyriq1 handoff/update: user reserved Lyriq2 for another task; its owned model test was aborted. Lyriq1 ZY22J58799 was updated from f66d3630 to exact Preview4 ee39113f using adb install -r. Installed hash matched. All 22 prior session IDs, connected openai/opencode providers and dark theme were preserved. Existing OpenAI OAuth produced gpt-5.6-luna responses before and after the update, each with three actual bash commands (pwd, uname -m, cat /etc/fedora-release), all exit 0. Evidence: lyriq1-preview4-before.json, lyriq1-preview4-after.json, ses_f76923882ffeELTxG9V48MnDIL-probe.json and ses_f7687c71cffeQ4b6AiFXEsqETG-probe.json. The startup briefly showed a blank WebView before becoming ready; this remains a UX issue. OAuth token refresh and the full provider matrix are not proven by these requests.

Final-candidate update/data preservation, free-provider model/tool smoke, touch rounds and 120-second screen-off recovery passed in the scopes above. OpenAI OAuth/Luna acceptance on locked Lyriq1 remains pending.
Finish the remaining app builds/debugging, collect installed artifact behavior, and report unsupported toolchains honestly.
Long Doze, credential-lock behavior, provider/token-refresh matrix, controlled fresh-root dnf5/dnfast comparison and full seven-journey release gate remain open.
Published Preview3 remains unchanged while this candidate is under test.

The preceding fe690f6e internal APK passed three 600-second screen-off rounds on Lyriq2, including real Fedora commands while off and preserved sessions. This is not credential-lock, prolonged Doze, or Preview4 acceptance.
The self-build recipe includes both debug native executables from retained source. Host rebuilding reproduced the FD seed hash c5711e31. Both executables also compiled on the ARM phone (evidence/pacman-native-self-build.json); differing NDK versions mean these are not byte-identical host/phone builds. Full self-build session ses_f76fdff87ffenxdzNOkkFDZKu2 failed on a truncated Fedora download (41438183/51427176 bytes). Transport failures now retry up to three times; checksum/signature failures remain fatal. Retry self-check passed, and real phone download verification is running in ses_f76a5ab88ffeIS6vUjhrtEM6fz. Full APK self-build is not yet accepted.

Pin/unpin persistence after reload passed in evidence/preview4-pin-touch.json. The test uses a native Android 220ms swipe; UI-only screen timeout changes are restored afterward. This is separate from screen-off acceptance.

Subsequent self-build progress: ses_f76a5ab88ffeIS6vUjhrtEM6fz completed both verified downloads (Fedora 51427176 bytes; OpenCode 60343887 bytes). Source ac4aec8888c89f3aeff8246c5f50ca9d9d79173f was freshly cloned on Pacman; full self-build ses_f76a39da8ffemjm6QrpEFaNJFB is waiting on the shared build slot. Earlier statements about the download still running describe the previous checkpoint.

AppFlowy native cargo-make stage completed in 4500.60 seconds; the current build is resolving Dart dependencies during code generation. The upstream wrapper suppresses pub output unless --verbose is passed. The retained recipe now invokes the same generator with --verbose; syntax was checked on the phone. The running build was not interrupted or changed. VLC bzip2 installation completed successfully (evidence/pacman-vlc-bzip2-confirmed.json).

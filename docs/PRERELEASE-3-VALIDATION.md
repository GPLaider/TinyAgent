# Preview 3 validation ledger

Target: private GPLaider/TinyAgent prerelease v0.1.0-preview.3. Development signing/package identity is retained for data-preserving updates; this is not a production-signed release.

Candidate: versionCode 2, versionName 0.1.0-preview.3; APK SHA256 e097d180038d1ba5b03bdda48440098f11c558861cd4c346a5baae0d82082858. Build passed; existing development signer verified.

Completed before candidate rebuild:
- Session swipe pin/delete, multi-select, Undo and project folder creation: actual Lyriq2 touch and host regressions passed; previous candidate installed on both Lyriqs.
- Three 15-second background/screen-off cycles: Fedora command, backend health and sessions survived. This does not validate long Doze, credential unlock or UI scroll restoration.
- Packaged harness, bootstrap, native notices, runtime archives and 952 GUI assets verified.
- dnfast16c6887 isolated app-UID GC regression passes after installation and repeated refresh without cache reset. The product launcher integration and controlled dnf5 comparison remain separate.

Further results:
- Prior candidate f66d3630 passed three two-minute screen-off cycles on retry. First long-test attempt lost a forwarded health response before screen-off, during background transition; no backend restart was required for subsequent health success. Preserve this failure rather than count an uninterrupted pass.
- Exact Preview3 APK installed in place on Lyriq2. Checked session list (100 returned IDs), backend credential fingerprint and connected-provider set survived the update. This device has opencode connected; this is not an OAuth refresh test.
- Exact Preview3 runtime stop/restart passed: app-UID backend processes stopped, CPU lock released, service restarted and lock reacquired; stay-on remained 0.
- Exact Preview3 passed three consecutive 120-second screen-off/background cycles: backend health, Fedora pwd-independent git hash command and session preservation. Evidence: lyriq2-screen-recovery-120s-prerelease.json.
- Exact Preview3 passed three consecutive raw-CDP touch runs: long press, two selections, bulk-delete Undo, swipe-delete Undo without modal, project bulk/swipe Undo. Evidence: preview3-touch-01/02/03.json. Earlier driver attempts used stale fixtures or coordinates under sticky controls; the driver now creates fresh fixtures and centers/rechecks targets. No app change was made to turn those driver failures into passes.
- APK code differs from the preceding candidate despite only a version setting change in this build step; native/GUI/runtime packaged hashes passed and device acceptance above was repeated on the new artifact. Do not assume byte-identical DEX.

- Current-candidate opencode/big-pickle (catalog reports zero input/output cost) response plus completed bash `/usr/bin/pwd` tool passed in 27.859s. A dedicated QA session was used. This does not cover paid/OpenAI OAuth token renewal.

Open:
- Candidate source snapshot, privacy review, private release asset upload and download verification.
- Full clean install, provider matrix, six application builds and production release three-round gate are not yet complete.

Do not treat historical evidence from other hashes as new-candidate acceptance.

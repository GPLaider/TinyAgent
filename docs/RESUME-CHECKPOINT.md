# Restart checkpoint — 2026-09-08

## Latest checkpoint: v20 wireless integration verified

Current target remains Lyriq1 ZY22J58799 (100.79.134.53:5555); Flip7 untouched.
v20 is installed, SHA256 0cfbd92efea5445df2d9ddedd1491f84d7a01151b4a3b48c184248cb4d405f3d,
same development certificate. App UID10000, latest PID15442. Fedora/OpenCode runs.
User requested complete wireless Developer entrance and strict Stock independence.
Implemented pinned LibADB BC source, dynamic local mDNS, notification pairing,
key persistence, verified shell UID2000 and TLS streaming APK install.
Android wireless debugging is now enabled by UI on1; TinyAgent paired through its
own RemoteInput notification. Port changed41255->34377 with successful discovery.
v20: reconnect3/3, install3/3, Stock rejection plus Fedora Git survival passed.
v19 real WebView/Fedora bridge verified actual Developer UID2000. v17 Git/Fedora
3/3, old sessions retained and navigation3/3; force-stop/reopen recovered.
No personal OAuth/model inference this run. See docs/WIRELESS-DEVELOPER.md.
Private preview2 is published: https://github.com/GPLaider/TinyAgent/releases/tag/v0.1.0-preview.2.
Export commit a63d4093aebfd39e30b3cef0a2dd4fa6e6d58d11; canonical source commit
9225ae95e968b821e81cc978715e37252c12cd78. Repo private, prerelease true, draft false.
Downloaded APK hash matches the device-tested v20. Verification saved at
D:/TinyAgent-work/github-private/private-release-preview2-verification.json.
No build/transfer/server/installer test remains running. WebView forward19222
removed. Lyriq1 left in TinyAgent conversation UI, Fedora running, Developer
wireless pairing retained, Root unchecked. Do not operate Flip7.

## Earlier resumption record (historical)

Lyriq1 v16 first install succeeded. UI Prepare unpacked Fedora and started
OpenCode as Android UID10000, Enforcing. Real WebView API and harness worked.
Git was absent from the minimal image; three shell results confirmed the defect.
The shell API's `completed` state did not indicate command success.

v17 adds missing basic development package installation to LocalLinuxRuntime.prepare.
Build/lint/packaged checks passed; APK SHA256
`a7ed1e9ce41c5d0741d8679bbc134cf9aa5b15dc64eaf0109649e4395ffd11ed`,
same development certificate as v16. v17 is installed on1 as an update. Its
ordinary app process is11086; microdnf package installation was running at the
latest checkpoint. Observe with scripts/observe-lyriq1-setup.py v17, then forward
19222 to current app WebView and run scripts/check-lyriq1-webview.mjs v17.
These scripts do not require run-as, which this ROM denies. Never infer absent
app files from failed run-as. No Flip7 operation. Preview2 still unpublished.

The older details below describe the pre-resume state and are historical.

Safe to restart Codex now. No build, transfer, installer client or one-shot HTTP
server from this task remains running. The Android app-owned backends on other
test phones may continue normally; do not stop them just to restart Codex.

## Latest user direction

- Test on **Lyriq 1**, hardware **ZY22J58799**, ADB **100.79.134.53:5555**.
- **Do not operate Flip7. User is using it.** Tailscale inventory only identified
  it; no ADB connection, package install, settings change or UI operation occurred.
- User correctly requires stock functionality without app ADB/root dependency.
  A host ADB connection for installation/UI/log instrumentation is fine. Do not
  conflate host observation with application self-ADB dependency.
- Modern wireless debugging is not port 5555. Pairing/TLS plus distinct dynamic
  pairing/connect ports are still unimplemented; never claim manual port entry fixes it.
- GitHub **must remain PRIVATE**. User explicitly corrected the initial assumption.

## What changed and was checked

Canonical repo: `D:/TinyAgent-work/tinyagent`, master, committed fix **2313bf9**.
Fixed production PRoot factory to set `PROOT_NO_SECCOMP=1` for unpack/version/backend.
Debug stock probe also sets it and uses a fresh isolated rootfs directory.
ADB diagnostics separated from Fedora; ADB is explicitly optional; root-specific
advice only for root mode. Removed implicit 5555 defaults from Activity, installer
and Android bridge; saved explicit settings remain.

User screenshot: stock Flip7 PRoot `/system/bin/tar` execve EPERM, suggesting
PROOT_NO_SECCOMP=1. Missing setting confirmed in actual old running PRoot.
New setting verified in actual app-owned processes. This is a compatibility
candidate, not proof the affected Flip7 now works.

Pacman (USB 000501423003390) v15 fresh diagnostic Fedora extraction/identity
passed under UID10225, SELinux Enforcing while TCP adbd was disabled (port0).
Regular v15/v16 backend command also passed without app self-ADB. Host USB ADB
observed these checks. **Pacman TCP port restored to original5555** afterward.
No data was cleared. Existing rootfs/session/signing keys preserved.
Android build/lint and all packaged checks passed; Java policy99 passed.

## Final compatibility APK v16

`D:/TinyAgent-work/artifacts/tinyagent-capabilities-v16.apk`
SHA256 **9959ca8f39548b24e3a572505c270ac76aa6fd056ff060980f279b66ee8922ad**.
Existing development certificate SHA256
**a3ef78ae0bfdfc30307e3448e138eca29adf39d966f89af116bbce151abc1ed2**.
No new signing key. APK internal version still0.1.0-dev/code1.
v16 is installed on Pacman. Edge2 remains previous v14. No Flip7 operation.

## Lyriq 1 current exact state / first thing to resume

Verified hardware ZY22J58799, ADB UID2000, Enforcing, /data196GiB free.
TinyAgent package was absent before work and remains absent at checkpoint.
Screen was Dozing; woke once and requested normal keyguard dismissal.
`dumpsys trust` still deviceLocked=1; **user was asked to unlock 1 once**.

A slow `adb install -r <host v16>` client was started but not completed.
After verified alternative file transfer, **only its exact Windows adb client
PID23568 was stopped** (command line matched target1+install+v16). Do not restart
that slow streamed upload. ADB server and device were not stopped or rebooted.
Final `pm path io.github.gplaider.tinyagent.debug` returned no package.

The complete APK is already on1 at **/data/local/tmp/tinyagent-v16.apk**.
Its SHA256 was measured after transfer and exactly matches above. It arrived via
phone-native curl over Tailscale from a one-shot host HTTP server bound to the
host Tailscale interface and restricted to the source IP of Lyriq1. That server
served the one request and exited. No public listener remains.

Resume:
1. Recheck serial and remote APK SHA256. Recheck `pm path` in case any install
   completion raced the cancellation; never uninstall/clear data.
2. Install the existing remote APK with direct argv:
   `adb -s 100.79.134.53:5555 shell pm install -r /data/local/tmp/tinyagent-v16.apk`
3. Confirm owner unlocked screen before UI checks. Do not bypass credentials.
4. Run new `scripts/check-lyriq1-first-setup.py` using bundled Python. It checks
   no prepared-v1 and no app ADB identity, taps actual Environment Prepare, waits
   up to600s, then verifies app-owned PRoot/OpenCode UID and authenticated health.
   **Do not remove prepared-v1 or reset data to force this first-run guard through.**
   If already prepared, inspect actual state and use recovery checks instead.
5. Probe backend via updated `scripts/probe-stock-backend.py --serial
   100.79.134.53:5555 --check-harness ...`. It maps hardware1 and host port14099.
6. Record evidence; publish compatibility preview only with actual verified scope.

## Uncommitted canonical files

- scripts/check-device-adb.py: added Lyriq1 mapping.
- scripts/device-ui.py: added Lyriq1 choice.
- scripts/probe-stock-backend.py: added Lyriq1/hardware/forward14099 mapping.
- scripts/check-lyriq1-first-setup.py: NEW, not run yet. Review before use; handles
  real first preparation, no root selection, no app ADB identity creation. A
  notification permission dialog may need normal UI handling.
- This checkpoint file.

## Private GitHub work in progress

Repo **https://github.com/GPLaider/TinyAgent**, PRIVATE/isPrivate:true reverified.
Private clean export checkout `D:/TinyAgent-work/github-private/TinyAgent`.
Remote main initially bd7085a; existing published prerelease v0.1.0-preview.1
contains v14 APK; remains unchanged. Keys/raw device conversations excluded.

Export checkout now has UNCOMMITTED copies of the five changed Android source
files plus docs/STOCK-COMPATIBILITY.md. Do not discard. New preview2 assets dir:
`D:/TinyAgent-work/github-private/release-v0.1.0-preview.2/`
contains `TinyAgent-0.1.0-preview.2-arm64.apk` (exact v16 hash above).
**No preview2 tag/release/upload has been created yet.** Need release notes,
signer report/checksums, source snapshot metadata update, commit/push, PRIVATE
gate, then private prerelease. Never create a public repo or change visibility.
Native source bundle from preview1 remains valid; native dependencies unchanged.
No Telegram completion report for this unresolved bug work has been sent.

## Tools

Python: C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe
ADB: C:/Users/Administrator/AppData/Local/Android/Sdk/platform-tools/adb.exe
Build: scripts/build-android.ps1 (JDK17/SDK36); apply shell-boundary skill.
No raw wsl/bash-c; shell grammar stays in versioned scripts.

Former tool sessions: streamed installer36303 (terminated client); one-shot
HTTP26220 and curl3598 completed. No session should be resumed as an active job.

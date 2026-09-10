# Current Lyriq1 screen-off validation — incomplete

Target: ZY22J58799 (`100.79.134.53:5555`), application UID 10042.
Installed APK: `TinyAgent-startup-recovery-2-clean.apk`, SHA-256
`f980ef990becc07fd1a36f363d3578b950039ae2b6f7121db0ddbe0e123df2a7`.
Owner explicitly authorized locking phone 1. No credential, keyguard policy,
root setting, battery exemption, or power policy was changed.

The first dedicated shell session was `ses_f75892a90ffeSv9xoHZj70Baua`,
command `/usr/bin/sleep 65`. During non-interactive `Dozing`, observed app
29306 → PRoot 31230 → OpenCode 31237 → bash 31706 → sleep 31732, UID 10042.
The initial verifier incorrectly required only `Asleep`; it stopped on the
observed `Dozing` state. The verifier now accepts either non-interactive state
and checks the display suspend blocker is released. This correction is not
itself a product pass.

Later observation found the app, PRoot, and OpenCode still alive and the shell
children gone. The WebView CDP result read timed out behind the credential lock.
Therefore exit status and successful completion remain unverified. The owner
was asked to unlock and return to TinyAgent; no keyguard dismissal was issued.
After the owner unlocked, the session readback confirmed completed, exit 0,
start 1789029439291 and end 1789029505615 (device Unix milliseconds).
The interrupted observation did not preserve a complete screen-off interval,
so this proves successful execution but not completion before wake.
Readback: `evidence/ses_f75892a90ffeSv9xoHZj70Baua-probe.json`.
The owner subsequently reassigned screen-off testing to Lyriq2. Do not rerun
the Lyriq1 lock script without a new target change.

The three-round checker records the installed APK hash, device-clock wake
time, power state, actual processes, and tool completion state. It preserves
partial evidence before waking or reading the WebView. A completed shell
must have exit 0 and an end timestamp before wake. These 65-second probes
cover short screen-off continuity only; they do not prove long Doze, model
streaming, network transitions, UI restoration, or the full release gate.

ADB currently runs as UID 2000. `run-as` returns
`setegid(AID_PACKAGE_INFO) failed: Operation not permitted`; this blocks the
existing host API verifier's credential access, not the phone-local backend.
Existing WebView authentication is used without copying OAuth credentials.

## Reassigned Lyriq2 observations

ZY22HZPLL8 retained its existing Preview4 APK, SHA-256
`ee39113fad165b1e7b3a8548c2886739c143bcbdbb7f596e4aaf94b3cef7e606`.
The backend was idle before dedicated test sessions were created. The existing
screen recovery script gained `--keep-locked`, suppressing keyguard dismissal
and UI foregrounding. Three 60-second screen-off observations passed with
actual Fedora sha256sum execution, backend health and all three test sessions
retained. This was one continuing screen-off interval with three checks, not
three unlock/relock cycles. The device remained asleep afterward.

During observation Android reported `mWakefulness=Asleep`, app UID10151 CPU
wake lock, and trust `deviceLocked=0`. Thus this proves screen-off execution,
not credential-lock handling. No password was entered or changed. Evidence is
the timestamped `evidence/lyriq2-screen-recovery-60s-*.json` report. These
results must not be attributed to the newer Lyriq1 APK.

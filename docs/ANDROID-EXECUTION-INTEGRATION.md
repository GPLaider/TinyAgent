# Android execution integration

## Updated real-device evidence, 2026-09-11

The historical gap below is now implemented through AndroidJobs and the
existing SelfAdbClient. The production `tinyagent-android.py` exposes authorized
shell/install jobs, UUID status inspection and cancellation. Stock remains
independent of ADB. Developer requires UID 2000; Root requires UID 0.

Lyriq2 ZY22HZPLL8 passed Root identity, exit 7 with separate stderr, actual
running-process cancellation, app restart retaining the same remote PID/start
ticks, and successful result recovery. The client installed the test-only
`io.github.gplaider.tinyagent.installprobe` version 1; PackageManager independently
confirmed installation. See evidence/android-jobs-lyriq2-{root-id,result-cancel,
recovery-before,recovery-after,install}.json.

DeepSeek 4.1 Flash itself performed identity, installation and PackageManager
queries (evidence/deepseek-41-android-jobs-root.json). Its concurrent queries
exposed rejection and a completion-status race; recovery did not count as a
clean pass. The corrected APK SHA256 is
ed1653d2da0f397777d2ac46049ec37ab48c6b10522a0891a45c90a7de5e12c3.
Exact signed bytes were verified before a data-preserving update on Lyriq2.
Its bounded FIFO, queued cancellation, six short commands with zero exits,
and safe unknown-ID rejection passed through the actual phone-local backend:
evidence/android-fifo-lyriq2.json. Runnable phone-Fedora check:
scripts/check-android-jobs-live.py (authorized Root and fixture required).

DeepSeek concurrent-query retest passed: evidence/deepseek-41-fifo-retest.json,
session ses_f73a37b79ffewmKERBaIchf7bn. Tool invocation intervals overlapped
(1789061306973..1789061310981 and 1789061307197..1789061312170); both returned
actual Android exit 0 and confirmed installed version 1. No busy rejection or
spurious unknown state occurred.

The corrected candidate also passed exit 7/stderr and running-process
cancellation: evidence/android-fifo-running-cancel.json (session
ses_f73a0efbdffe7m9HjCQxvNvJsA).

Lyriq1 ZY22J58799 subsequently passed native Developer shell execution on
runtime12 after the user enabled Android Wireless debugging and the app
reconnected its saved key. DeepSeek V4.1 Flash read the live harness, invoked
one managed client job without raw adb, and received `verified_self=true`,
`execution_uid=2000`, Android cwd `/data/local/tmp`, the expected serial/device,
empty stderr and exit 0. See evidence/lyriq1-ladb-developer-success-full.json
and evidence/ladb-developer-runtime12-validation.md.

Still pending: native Developer installation; recovery cancellation after FIFO
changes. Release and six-app campaign remain unfinished; this APK uses the
debug identity.

## Historical failure and initial implementation notes

### Developer connection follow-up

Lyriq1 ZY22J58799 was updated without data reset to the same FIFO candidate.
Session ses_f739af23dffe3bHRrYV1XbizRR submitted Developer job
a34b47de-79ae-4e96-8d64-efa19e5111c7. The phone's self-ADB connection timed out;
no command was started and no Developer success is claimed. The locked phone
prevents checking the user authorization dialog; an unlock/approval request is
pending. This exposed an inaccurate `unknown` result before any submission.

AndroidJobs now distinguishes pre-submission failure (`failed`, exit unknown)
from uncertain remote submission/recovery (`unknown`). Build/lint and packaged
runtime checks pass. Candidate SHA256
e8a17ccbc72968337c831e42f11f538032bb4fe8513f55aa8d26e1c30bdb0ff9
is installed on Lyriq1, preserving data. The CDP observation timed out after
120 seconds; the original session was subsequently recovered without replay:
ses_f7396b57effeRqx1oMLsg7Cjs6, job080534b9-c832-45bb-85be-13ad41013b58.
It correctly returned failed, null remote exit and client exit 1 for the same
pre-submission connection failure. Evidence:
evidence/go-campaign/lyriq1-ses_f7396b57effeRqx1oMLsg7Cjs6-1789062365481.json.
This verifies the state correction, not successful Developer access.
Lyriq2 still runs ed1653d2 because its
dnfast refresh is active; do not interrupt it for this update.

The app has verified self-ADB installation, while AndroidDiagnosticsBridge only
exposes GET inspection. User explicitly requires agents to perform authorized
Android work, not send the user back to native buttons. Native ADB connections
are not visible in Fedora's separate `adb devices` list.

Current implementation progress: common AdbShellResult reads bounded shell-v2
stdout/stderr separately and preserves nonzero exit. WirelessAdb's existing
diagnostic API reuses it; SelfAdbClient.execute revalidates the previously
verified UID immediately before execution, and returns the same result type for
wireless and Dadb transports. Plain Java regression passes Korean stdout,
separate stderr, exit 7, truncated stream and oversize rejection. Android Java
compilation passes.

Still pending: expose authorized execution and install requests to the agent,
real remote process cancellation (closing the client alone is not proof),
durable task status after reconnection, workspace artifact validation, and
measured command examples. Do not describe this building block as a usable
agent execution bridge yet. Stock must retain app UID execution and Android
approval installation; Developer must enforce shell UID 2000, Root UID 0.

Runnable check: compile AdbShellResult.java with scripts/AdbShellResultCheck.java
and run io.github.gplaider.tinyagent.AdbShellResultCheck. No new dependency.

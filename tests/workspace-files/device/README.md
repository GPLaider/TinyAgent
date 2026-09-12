# Android app-UID and Binder probe

This standalone Gradle project builds two ordinary test APKs. It copies exactly
the production `WorkspaceFiles.java`, `WorkspaceFileProvider.java` and
`WorkspaceCopy.java` and `InstallerActivity.java` into a
generated source directory, packages AndroidX FileProvider, and runs the provider
in a separate process. It does not rebuild or install the TinyAgent application.

Prerequisites: JDK 17, Android SDK 36, Gradle wrapper from the repository, adb,
aapt2 and apksigner. On ARM Linux, pass a compatible aapt2 override if needed.
Create a **probe-only** signing key outside the repository (password below is
public test configuration, never a release-key password):

```sh
keytool -genkeypair -keystore /absolute/probe/probe.p12 -storetype PKCS12 \
  -storepass workspace-probe-only -keypass workspace-probe-only \
  -alias workspace-probe -keyalg RSA -keysize 2048 -validity 30 \
  -dname 'CN=TinyAgent Workspace Regression Probe'
keytool -exportcert -keystore /absolute/probe/probe.p12 \
  -storepass workspace-probe-only -alias workspace-probe \
  -file /absolute/probe/probe.der
sha256sum /absolute/probe/probe.der
```

Record this certificate SHA256 before building and retain it for the runner's
`--expected-signer`. Build from the TinyAgent repository root:

```sh
bash ./gradlew -p tests/workspace-files/device --no-daemon \
  -PprobeBuildDir=/absolute/probe/build \
  -PprobeKeystore=/absolute/probe/probe.p12 \
  assembleOwnerDebug assembleClientDebug
```

Run against the exact authorized serial:

```sh
python3 scripts/check-workspace-device.py --serial DEVICE_SERIAL \
  --owner-apk /absolute/probe/build/outputs/apk/owner/debug/WorkspaceDeviceProbe-owner-debug.apk \
  --client-apk /absolute/probe/build/outputs/apk/client/debug/WorkspaceDeviceProbe-client-debug.apk \
  --expected-signer CERTIFICATE_SHA256 \
  --apksigner-jar /absolute/sdk/build-tools/35.0.0/lib/apksigner.jar \
  --aapt2 /absolute/aapt2 \
  --report /absolute/probe/device-report.json
```

The runner verifies APK application IDs and signers, refuses pre-existing probe
packages, requires completed boot and SELinux Enforcing, and preserves the
installed TinyAgent release/debug APK paths. Only the two fresh probe packages
are installed and removed. Every instrument call has a 60-second timeout and
cleanup results are recorded even after failed assertions.

Coverage: actual app UID, file mode denial, malformed paths, external symlinks,
FIFO rejection, CLOEXEC, opened-inode lifetime, Unicode URI handling, 300 rounds
of local/Binder reads and rejected reads, real bitmap decoding, WAV metadata
through a Binder URI, and a detached dup FD surviving provider process death confirmed by ESRCH,
after closing its unstable Binder client lease. Both
consumer and remote provider FD counts are checked.
Separate app UIDs test denial before grant, exact read grant, no write/other-URI
access, and denial after revocation. A test-only signature-protected control
provider grants and revokes during one client instrumentation run, because
restarting instrumentation can clear URI grants. The artifact provider remains
non-exported and uses the unchanged production implementation. Device tests complement deterministic
check/open race injection in the host suite; they do not validate every codec,
TinyAgent UI navigation, full-app process restoration or per-session sandboxing.

Observed Android limitation: killing a provider while retaining a stable
ContentResolver lease can cause Android to kill the dependent consumer process
as well. The detached-FD test does not promise stable-client process survival.

The Android probe additionally captures the opened FD size, truncates/appends
the original inode, and verifies bounded-copy failure instead of false success.

## Actual Activity recreation

Pass `--activity-recreate` to the device runner to exercise the production
InstallerActivity export UI inside the isolated probe. The test APK supplies
compile-only install dependencies, a platform dialog style resource, an
Instrumentation monitor that returns a controlled document-picker result, and a
local reliable-pipe destination. No real APK install route or external document
picker is used by these cases.

The destination blocks a 512 KiB export while `Activity.recreate()` runs, then
completes or injects an output failure. Assertions require one destination open,
exact copied bytes on success, completion of the recreated success screen, and
a visible failure on the recreated error screen without silent dismissal or
replay. This is actual Android Activity recreation, not OS process-death recovery.

The same flag also runs `activity-isolation`: export A fails and remains open,
then a distinct Activity exports B successfully. A must retain its failure while
B completes exactly one 512 KiB copy and closes. Sentinel installer preferences
verify that export results do not change installation status, and unrelated
installation updates do not replace the export failure. The second Activity is
launched from the first with a bounded monitor; reusing a NEW_TASK root intent
can reuse the existing task and stall `startActivitySync`.

Two more modes run with that flag:

- `activity-dismiss` closes an Activity during a blocked export and opens a new
  invalid-source export screen. It releases the old copy and waits for the old
  executor to terminate (reflection is used only as a completion barrier).
  The copy must complete once and the fresh error screen must remain unchanged.
  Closing a screen is not asserted to cancel an already authorized copy.
- `activity-status-switch` uses the real full-screen buttons to validate an
  empty source in install/export/install order. No installation or document
  picker is reached. The last error must replace the export error even though
  the installer preference string equals its previously stored value.

The flag also runs four `activity-picker-*` modes (`save`, `cancel`, `null`,
`empty`). A monitor redirects ACTION_CREATE_DOCUMENT to a non-exported,
probe-only Activity, preserving the actual delayed Activity result delivery.
The parent InstallerActivity is recreated while this picker is open. Assertions
require no destination before selection and exactly one picker launch. A valid
result must copy the original 73 KiB random payload exactly once, including a
SHA-256 comparison. Cancellation, RESULT_OK with null data, and RESULT_OK with
no URI must close the export screen without opening the destination. These are
Android Activity-result lifecycle checks, not system DocumentsUI integration or
whole-app process-death restoration.

## Actual stopped-process death

Add `--process-death` to exercise three real owner main-process deaths from the
separate client instrumentation. Combined with `--activity-recreate`, this runs
23 instrumentation steps, including the pending-result cases below. A signature-protected probe-only root Activity alias
and control provider expose only the isolated owner to the paired signer. A
test Application records lifecycle callbacks; it injects a selected source into
the actual production export result handler on the full-screen Activity, so this
phase does not run a picker or an APK install transaction.

The client starts a blocked 512 KiB copy and backgrounds the task. The runner
requires onSaveInstanceState and onStop, captures the exact owner PID and task,
closes unstable provider leases, and runs `am kill` for that isolated owner
package only. It verifies the PID is absent before restoring the same root task.
The new PID, same task ID, OS-supplied saved Bundle and zero output reopens are
required. It does not use force-stop, clear data, reboot, root or a new manually
constructed saved Bundle.

Phases: (1) death during blocked copy, (2) completion before saved state, (3)
completion after saved state but before death. In (1) and (3), the saved running
state cannot prove the final result, so the UI must say to check the destination.
In (2), the saved completed status must survive. No phase restarts the copy.
This validates stopped-process restoration of the isolated full-screen Activity,
not low-memory scheduling, every crash/task-removal path, actual external SAF
persistence, or automatic copy resumption.

### Pending picker result across owner death

The same `--process-death` option also runs `death-picker-save`, `-cancel`,
`-null` and `-empty`. A signature-protected Activity in the paired client remains
alive while the stopped owner schedules termination of only its own verified
PID. The source selection is seeded in the production Activity and an actual
`startActivityForResult` call opens the client picker. All unstable provider
leases close before death; ESRCH must be observed before returning the result.

Android must then recreate the original parent with a new PID, the same task ID
and its own saved Bundle. The valid result copies a seeded random 512 KiB source
exactly once, verified by SHA-256. Cancellation and malformed results must show
cancellation with zero output opens. This uses a test picker, not DocumentsUI.
Only the probe-owned task is removed after each case, and Activity destruction
is awaited before the next case to prevent test-state carryover.

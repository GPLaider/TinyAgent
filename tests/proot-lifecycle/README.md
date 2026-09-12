# Isolated Android PRoot lifecycle check

Run `scripts/check-proot-lifecycle-device.py` with `JAVA_HOME` (JDK 17),
`ANDROID_HOME` (API 36), `adb` on PATH, and these required arguments:

```text
--serial DEVICE --build-tools HOST_NATIVE_BUILD_TOOLS --result RESULT.json
```

The runner compiles the current production runtime classes, verifies the pinned
PRoot/native and Fedora hashes, and installs a temporarily signed APK under
`io.github.gplaider.tinyagent.prootaudit`. It refuses to replace an existing probe
package and uninstalls its package in `finally`. This device check currently
requires an already running TinyAgent debug app and records its PID before and
after; it does not access that app's files, credentials, or backend.

The probe extracts Fedora 44 into its own app UID and checks:

- Three rounds each of production cancellation, recovery SIGQUIT, and verified
  native SIGKILL, including PRoot parent and Fedora child death and PID cleanup.
- Interrupted/timed-out launch before PID publication, with no guest started.
- Wrong boot ID/start ticks cannot signal a live same-UID sentinel.
- Killing only a separate probe Java service process, then recovering its
  PRoot/Fedora child through a fresh production runtime instance.

`Process.destroyForcibly()` is deliberately not used to simulate PRoot SIGKILL:
on the tested Android runtime it did not terminate PRoot. The kill check invokes
the production verified signal helper. Pre-publication failure checks block the
launcher before `exec`, matching the real launch protocol.

Allow several minutes for compilation, APK transfer, and Fedora extraction.
The instrumentation timeout is 180 seconds. JSON evidence includes source,
native, Fedora and APK hashes, instrumentation output, and uninstall status.
This checks native lifecycle; it does not run OpenCode, a model, package
transactions, screen-off scenarios, or other OEM power policies.

## Shipped OpenCode integration

Add `--backend` to run the separate `BackendLifecycleCheck` instead of the
PRoot-only suite. It also verifies and packages the pinned snapshot-12 archive.
The probe uses an ephemeral loopback port, random local HTTP password, its own
HOME/workspace/database, and disables provider discovery/default plugins and
auto-updates. No existing app authentication or backend endpoints are used.

This suite runs actual OpenCode session shell commands without model inference:
authenticated health and session creation, unauthenticated request rejection,
normal command output, exit-code 7 preservation, recovery environment flag removal, two rounds each of
HTTP abort, production runtime cancellation, and native tracer SIGKILL. It checks
real Fedora child death, persisted partial output, terminal tool states, restart
recovery metadata, idle session status, and survival of completed message history.

The real `guest/start/cancel/signal/recoverPreviousProcesses` methods are used.
`startBackend`/`awaitBackend` are not called because they hardcode the user's
4097 endpoint; the probe constructs its own server command and health request.
This is not full `RuntimeSetupService.prepare()` integration: no package install,
Android bridge, model request, UI, or power-management claim. The backend mode
allows 420 seconds for instrumentation, including fresh Fedora/OpenCode unpack.

# Runtime service lifecycle regressions

Host checks compile the complete production `RuntimeSetupService` inside the
test template, removing imports and making the enclosing class static. All
production methods remain unchanged. Deterministic Android/executor doubles
deliver START during cleanup and retain stale monitor/network callbacks.

```sh
JAVA_HOME=/path/to/jdk python3 scripts/check-runtime-service.py
```

Checks cover retry during cleanup, duplicate START, STOP→START→STOP, failed
network registration/unregistration, destroyed instances, delayed old workers,
wakelock release, callback ownership and startId-specific service termination.
The pre-fix service fails with `old worker stopped the retry generation`.
This is callback-order evidence, not a real Android scheduler test.

The device test installs a separate temporary package,
`io.github.gplaider.tinyagent.runtimeaudit`. It refuses to replace an existing
package with that ID and removes only its own successful installation in finally.
It compiles the actual service against Android API 36, with a test runtime that
owns only `/system/bin/sleep` children. It uses a new temporary test signing key.
It does not install a TinyAgent update or use an existing workspace, OpenCode
port, ADB key, PRoot runtime or model credentials.

```sh
JAVA_HOME=/path/to/jdk ANDROID_HOME=/path/to/sdk \
python3 scripts/check-runtime-service-device.py \
  --serial YOUR_DEVICE_SERIAL \
  --build-tools /path/to/host-native/build-tools \
  --result /path/to/results.json
```

Three device rounds hold the old runtime in cleanup, deliver a new START, then
verify the replacement runtime, its monitor, real wake lock, explicit STOP and
test-child exit. The foreground service, Handler, Android startId delivery and
wakelock implementation are real. Fedora, PRoot and privileged Android jobs are
test doubles and require separate integration checks. The build-tools directory
must contain host-native aapt2/zipalign plus lib/d8.jar and lib/apksigner.jar.

## Output pipe regression

Add `--output-only` to the device command to compile the production
`RuntimeProcessOutput` with `output/RuntimeOutputDeviceCheck.java` instead of
the service fixture. Three real Android shell children each print CR, wait for
a callback acknowledgment on stdin, then emit a delayed LF and a second CR.
The check requires prompt callbacks, correct CRLF/non-LF/EOF behavior, exit 7,
and child/reader termination. No PRoot, service, model or package work runs.
The runner records the existing debug PID before and after, so this harness
currently requires that app to be running. Its contents are never read.

The host `RuntimeProcessOutputCheck` also covers this handshake. The earlier
bounded reader attempted to read the byte after CR before delivering the line,
so the callback and child deadlocked. The reader now defers optional LF skipping
until the next call, matching BufferedReader's immediate CR delivery while
retaining the line-length limit.

# Workspace failure regression

Run on Linux as an unprivileged user with a JDK and C compiler:

```sh
JAVA_HOME=/path/to/jdk python3 scripts/check-workspace-files.py
```

The runner compiles the production `WorkspaceFiles` and `WorkspaceFileProvider`
classes. Small Android API doubles delegate open, dup, fstat, readlink, fcntl and
close to actual Linux syscalls through the test-only JNI library. Host doubles are not packaged into the production APK. All fixtures/build files are temporary.
A 30-second subprocess timeout bounds regressions such as a blocking FIFO open.

`Os.beforeOpen` swaps a path deterministically between production validation and
open. Tests reproduce the previous check-then-open disclosure, then reject leaf
and parent symlink swaps, FIFO swaps, disappearing files, invalid paths and
replaced workspace roots. Permission-denial tests run with real mode 000 files.
Injected dup/fstat/readlink/fcntl failures exercise cleanup; 500 cycles verify
that native descriptor counts stay fixed without requiring garbage collection.
The returned FD remains readable after the original FD is closed, remains on
the opened inode after path replacement, and retains FD_CLOEXEC. Provider tests
cover encoded filenames, malformed URIs, write/delete rejection and path swaps.

The export harness compiles the production pending-selection declaration,
restore statement, save method, export method and activity-result method against
small UI doubles. It verifies independent activity selections, saved-state
recreation, cancel/duplicate/overlapping results and a denied document picker.

These tests are host evidence, not Android instrumentation. Real Binder URI
permission enforcement, vendor SELinux access to `/proc/self/fd`, multimedia
codec behavior and OS process death still require device verification. The FD
check is a containment check, not an immutable snapshot: another writer can
modify bytes in the same inode. Workspace directories remain shared by the
app's sessions; this patch does not create separate per-session sandboxes.

See `device/README.md` for the separate Android app-UID/Binder probe and its exact
install/remove boundary. It complements this host suite.

`WorkspaceCopyCheck` exercises the production finite-length copier against a
continuously growing stream, truncation, invalid sizes, read/write failures,
zero-progress reads and interruption. The export activity harness also mutates
real source files at destination-open/write time, then injects 250 destination
open/null/write/flush/close failures and checks both failure reporting and FD
cleanup. Initial-size copying detects shrink/growth, not same-size content edits;
it is not an immutable snapshot or an atomic SAF publication.

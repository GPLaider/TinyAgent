# TinyAgent dnfast launcher (integration candidate)

`dnfast-launch.c` runs as the Android app before PRoot. It validates kernel UID/GID
and zero effective capabilities, opens the root without following ancestor symlinks,
holds an exclusive nonblocking root flock, persists a root ID, prepares the private
state directory, and creates the canonical launch context agreed with dnfast.
The root/lock and immutable context are inherited as FD5/FD6. It then execs PRoot.

The caller must supply app-pinned runtime/bind/binary hashes and an app-selected
PRoot argv. Those inputs are not an authentication boundary against same-UID code.
The receiver must independently validate the context, root/state identities,
binary hashes, backend binding and migration/recovery state before any mutation.
The debug DnfastProbeActivity invokes this launcher and the isolated app-UID
transaction cycle has passed. The ordinary OpenCode command path does not invoke
it yet; this is not production transaction integration.

```
libdnfastlaunch.so ROOT EXPECTED_UID RUNTIME_HASH BINDS_HASH DNFAST_HASH EXECUTOR_HASH -- PROOT ARGS...
```

The initial app memfd mode is exactly0666 with no pathname links and F_SEAL_EXEC;
the final seal set is exactly47. No chmod fallback exists. Android SELinux domain
and category checks apply. This does not claim secrecy against same-UID code or
unverified cross-app procfd access. Regular root-ID files remain0600 and the final
state directory0700. Invalid root IDs are never silently regenerated. Interrupted
root-ID staging may leave an ignored64byte staging file; the published ID is atomic.

Build using `scripts/build-dnfast-launcher.py` with installed NDK28.0.13004108.
It stages only the debug native library. On an ARM Linux host, compile and run
`dnfast-launch-test.c` with C11/O2/Wall/Wextra/Werror. Controls cover exclusive locks,
persistent IDs, symlink and mode rejection, corrupt-ID rejection and immutable
nonexecuting context. Tests create a disposable `/tmp/tinyagent-launch-test-*` root;
no RPM, mount, user workspace, provider or journal is touched.

Real Android integration still needs an app-owned request transport: OpenCode bash
already runs inside PRoot and cannot create a pre-PRoot launcher merely by renaming
a command. Reuse the existing same-UID LocalSocket pattern, but preserve the current
read-only diagnostic endpoint's contract. A launcher request must expose actual
stdout/exit and interruption state. PRoot termination is not successful RPM rollback.

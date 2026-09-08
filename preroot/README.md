# PreRoot

TinyAgent owns and builds PreRoot. Version 0.1.0 implements the Fedora execution
entrypoint using Android Toybox unshare/mount/chroot and Fedora GNU env. It is
not PRoot and is not a security sandbox. Only explicitly selected
`unrestricted-root` is implemented; other modes fail before execution.

Execution provider IDs are `android-self-adb` and `fedora-preroot`. Model
providers retain upstream OpenCode IDs (for example `openai`, `anthropic`,
`opencode`); they are a separate namespace, not execution environments.

The product installation layout is `/data/local/tinyagent/`:

- `runtime/<version>/`: immutable PreRoot scripts and Fedora rootfs.
- `data/`: persistent backend home, credentials and session database.
- `workspaces/<session-id>/`: persistent session workspaces.
- `shared/`: explicit Android/Fedora file exchange.
- `run/`: measured process identity and runtime state.

`prepare.sh` now provisions the pinned bundled archives into a fresh version,
and `enter.sh` binds persistent home/workspaces/shared directories for this
installation path. App setup runs in RuntimeSetupService and probes the installed
OpenCode version. Device installation, reuse, backend start/stop and automatic
native authentication have passed component checks; see `docs/STATUS.md`.
The existing diagnostic root remains intact. Interrupted-install recovery,
DNS refresh and full updates remain unfinished.

Run through the verified root self-ADB connection with literal arguments:

    /system/bin/sh /path/to/preroot.sh ROOT unrestricted-root doctor
    /system/bin/sh /path/to/preroot.sh ROOT unrestricted-root exec /workspace /usr/bin/id

`backend.sh unrestricted-root start|status|stop` controls the prepared production
backend. It uses a file lock and validates PID/start ticks/boot ID, keeps server
authentication in private persistent data, and starts a dedicated process group.
The selected unrestricted-root mode reaches OpenCode via OPENCODE_CONFIG_CONTENT.
The native app handles the server password without exposing it to JavaScript.

`exec` preserves child stdout/stderr and exit status. It creates a private mount
namespace with one-way propagation before attaching proc/dev. The caller must
track and cancel the actual process tree. The backend manager stops its process
group; independently detached jobs still require additional lifecycle management.
Do not advertise restricted execution support.

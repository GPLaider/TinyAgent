# ADB onboarding — android-adb (Developer)

First read STOCK.md: the Fedora workspace and execution UID do not change when
ADB is connected. This is an optional Android capability, not another Fedora.

Read the current ANDROID_TOOL.md and run its Developer inspection command.
Proceed only when it returns verified_self=true and execution_uid=2000.
The native transport checks a fresh loopback challenge on this same device.
Port presence, device model alone and a previous session's result are not proof.
A root adbd UID 0 does not satisfy this Developer mode; do not silently switch.

For an agent-requested APK installation, invoke the Android job client below
with Developer selected; do not hand the task back to the user merely because
Fedora has no ADB device list. The APK must have a matching signer for an update.
Streaming installation runs
on the verified self-ADB connection. Failure is not authorization to uninstall.
Fedora's `adb devices` does not enumerate this app-owned connection. An empty
list does not disprove a successful native self-ADB inspection. Do not ask the
user to pair again or enable a fixed TCP port because that separate list is empty.
Developer installation uses the authorized self-ADB transport; Android's
PackageInstaller approval is the Stock route, not an extra Developer step.

First authorization is a user action: Developer connection setup guides Android
Wireless debugging pairing. The user enters the six-digit code through the
TinyAgent notification while the Android pairing dialog stays open. Pairing and
connection ports are discovered separately; no PC, Tailscale or existing ADB is
required. Never suggest `adb tcpip` as the way to obtain initial authorization.
The app stores its key privately and rediscovers the local connection endpoint
for subsequent operations. Selecting Developer is not proof of a live connection.

For authorized Android commands use:
`python3 /root/.tinyagent/bootstrap/tinyagent-android.py --mode developer --cwd / shell 'id'`
For an authorized install use the same client with `--mode developer install
'project/app/build/outputs/apk/debug/app-debug.apk'` (workspace-relative path).
The client records actual UID, cwd, stdout, stderr and exit status. Save its UUID.
Use `--id UUID status` to inspect/reconnect, and `--id UUID cancel` to stop that
job's verified process group. Client disconnection is not cancellation. An
unknown result requires inspection, never another installation/submission.
Output retains the last 32 KiB per stream; write large logs into the workspace
and retrieve them explicitly. Don't detach processes from the managed group:
daemonized descendants need their own recorded identity and recovery plan.
Parallel requests are queued by the bridge. An explicit rejected request does
not prove its proposed UUID was accepted. Never inspect an Android private path
with Fedora file tools; use the Android client and the accepted job's status.
Prefer invoking the client directly so its exit status is preserved. If adding
logging, capture `$?` immediately before any echo or other command changes it.
Shizuku is not provided. The bridge does not expose another device's ADB server.
Connection loss leaves Fedora available. Reconnect and remeasure before retrying
Android work; confirm the installed package before repeating an uncertain install.

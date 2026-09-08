# ADB onboarding — android-adb (Developer)

First read STOCK.md: the Fedora workspace and execution UID do not change when
ADB is connected. This is an optional Android capability, not another Fedora.

Read the current ANDROID_TOOL.md and run its Developer inspection command.
Proceed only when it returns verified_self=true and execution_uid=2000.
The native transport checks a fresh loopback challenge on this same device.
Port presence, device model alone and a previous session's result are not proof.
A root adbd UID 0 does not satisfy this Developer mode; do not silently switch.

To install a generated APK, use the native installer with Developer selected.
The APK must have a matching signer for an update. Streaming installation runs
on the verified self-ADB connection. Failure is not authorization to uninstall.

First authorization is a user action: Developer connection setup guides Android
Wireless debugging pairing. The user enters the six-digit code through the
TinyAgent notification while the Android pairing dialog stays open. Pairing and
connection ports are discovered separately; no PC, Tailscale or existing ADB is
required. Never suggest `adb tcpip` as the way to obtain initial authorization.
The app stores its key privately and rediscovers the local connection endpoint
for subsequent operations. Selecting Developer is not proof of a live connection.

The current agent bridge exposes inspection only. Shizuku and arbitrary Android
shell execution are not provided by this bridge. If the task needs them, report
the missing capability rather than fabricating commands.
Connection loss leaves Fedora available. Reconnect and remeasure before retrying
Android work; confirm the installed package before repeating an uncertain install.

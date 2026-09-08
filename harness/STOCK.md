# Stock onboarding — android-stock / fedora-local

Read this first when joining an existing session. Fedora and OpenCode run under
the Android application UID. Guest `id` may return 0; that is PRoot emulation,
never Android root. Read TINYAGENT_ENVIRONMENT.md and ANDROID_TOOL.md for the
current device, paths, socket and permissions; old conversation sockets expire.

1. Use the live Stock curl command in ANDROID_TOOL.md to measure Android app UID,
   device and SDK. Hardware serial may be unavailable; do not invent it.
2. Use OpenCode bash directly for Fedora. Confirm `pwd`, tool availability and
   session workspace before edits. Work in the session's directory under
   `/workspace`; `/shared` is the exchange directory, `/root` persists app data.
3. Existing tools first. Bootstrap only missing prerequisites when the task
   permits downloads/installations. Preserve source and credentials on recovery.
4. APK installation uses the native APK installation screen, Stock route, and
   Android's user confirmation. Neither `su`, mount nor ADB is a core dependency.

Android inspection is read-only. The bridge is not an arbitrary Android shell.
An absent optional ADB connection must not prevent Fedora work. Report actual
commands, working directory, output and exit status; recover uncertain writes
by checking the real files/processes first. Do not read signing/provider secrets.

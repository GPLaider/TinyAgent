# Root onboarding — android-root

First read STOCK.md. Fedora still runs under the application UID; detecting
Android Root does not convert the Fedora process into an Android root process.

Read live ANDROID_TOOL.md. Root ADB is detected automatically, without a toggle
or asking the user for a port. Root inspection requires verified_self=true and
execution_uid=0. Native self-ADB proves the same device
with a fresh app-private nonce. Never infer root from Fedora's emulated UID 0.
The last detection is not proof of a live authorized connection. Each operation
must respect current permission and task scope; do not use a stale transcript.

Agent-requested APK installation uses the Android job client below on this
verified Root connection; the user need not open a separate installer screen.
ROM direct PackageInstaller is separate and requires the actual INSTALL_PACKAGES
grant. Installing an ordinary APK never creates this privileged permission.
Do not flash, reboot, change SELinux, erase data or escalate to repair a probe.

The Android job client supports `--mode root shell 'COMMAND'` and `--mode root
install 'workspace-relative.apk'` through the freshly verified UID 0 connection.
Use only within the owner's task/permission scope. A failed Root check must not
silently switch privileges. Read ADB.md for job status/cancel/recovery semantics.
The legacy root environment on port 4096 and its /data/local data are
separate from the app-owned backend on 4097; never overwrite or silently migrate
them. Root access can reach sensitive files: do not print keys, tokens or signing
material. Inspect real package/files/process state before repeating writes.

# Root onboarding — android-root

First read STOCK.md. Fedora still runs under the application UID; enabling
Android Root does not convert the Fedora process into an Android root process.

Read live ANDROID_TOOL.md. Root inspection requires the user's Root selection,
verified_self=true and execution_uid=0. Native self-ADB proves the same device
with a fresh app-private nonce. Never infer root from Fedora's emulated UID 0.
Selection alone is not proof of a live authorized connection. Each operation
must respect current permission and task scope; do not use a stale transcript.

APK installation uses the native Root installer on this verified connection.
ROM direct PackageInstaller is separate and requires the actual INSTALL_PACKAGES
grant. Installing an ordinary APK never creates this privileged permission.
Do not flash, reboot, change SELinux, erase data or escalate to repair a probe.

The present agent bridge exposes read-only identity probes and is not a general
root shell. The legacy root environment on port 4096 and its /data/local data are
separate from the app-owned backend on 4097; never overwrite or silently migrate
them. Root access can reach sensitive files: do not print keys, tokens or signing
material. Inspect real package/files/process state before repeating writes.

# Core runtime and optional Android capabilities

The user superseded the root-required design on 2026-09-08. Tier 0 is mandatory.
Root may extend Android administration, but must never gate local conversations,
Fedora preparation, Git, compilation or APK generation.

| Mode | Linux/agent execution | APK installation |
| --- | --- | --- |
| Stock | Ordinary app UID, app-private workspace, bundled PRoot/loader | Android PackageInstaller with explicit user confirmation |
| Developer | Same local runtime | An actually paired/authorized ADB transport; shell UID verified before install |
| Root/custom ROM | Same local runtime by default | Explicitly selected root bridge or installer with verified INSTALL_PACKAGES privilege |

Developer options being enabled is not proof of ADB authority. Shizuku permission
is a distinct optional transport, not inferred from ADB or root. Root access does
not automatically give the APK platform-signature permissions. A custom ROM is
not proof that its PackageManager grants privileged installation to this app.

## Installation contract

- The user selects an available route. Failure never escalates privileges or
  switches routes silently. Lack of enhanced capabilities leaves Stock usable.
- Stock uses PackageInstaller sessions and REQUEST_INSTALL_PACKAGES. Open the
  Android per-source permission screen when needed; require user action, handle
  pending confirmation, cancellation, success and failure as separate states.
- Developer installation streams the APK through the authorized self-ADB
  connection and uses the package installer under verified shell UID 2000.
  A host `adb install` is development evidence, not an app implementation.
- Root installation executes through a verified UID 0 bridge, or directly through
  PackageInstaller only when the process really has INSTALL_PACKAGES authority.
  It must not modify SELinux policy, system files or permission allowlists to
  manufacture a capability. A ROM-integrated privileged installer is an optional
  separate integration with explicit permission grants.
- Every route verifies package, version and signing identity and records the
  actual installer result. Updates preserve data. Signature mismatches do not
  trigger uninstall/reinstall. Self-update recovery must survive the old process
  being killed and reconcile the expected package on the next launch.

API reference: [PackageInstaller](https://developer.android.com/reference/android/content/pm/PackageInstaller)
and [SessionParams](https://developer.android.com/reference/android/content/pm/PackageInstaller.SessionParams).

## Current code audit and evidence

The default application path now uses LocalLinuxRuntime and RuntimeSetupService:
Fedora and OpenCode run under the Android app UID in files/linux, on port 4097.
Preparation and conversation entry do not require ADB or root. The previous
root runtime on port 4096 and its /data/local data remain preserved; automatic
migration of those sessions/workspaces has not yet been implemented.

InstallerActivity implements user-confirmed PackageInstaller, verified UID 2000
self-ADB, verified UID 0 self-ADB, and direct PackageInstaller guarded by the
actual INSTALL_PACKAGES permission. Ordinary installation does not grant that
permission. Each of the first three routes passed three consecutive fixture
installs on the same capabilities-v8 APK; see the three evidence/install-*.json reports.

A debug-only StockProbeActivity was added to test the replacement execution
mechanism before changing production startup. It never calls ADB, su, mount or
chroot. It verifies the pinned Fedora archive, extracts it with bundled PRoot,
and runs Fedora cat/id under the ordinary app UID. The PRoot executable and its
loader live in Android's extracted nativeLibraryDir, not writable app storage.

On Nothing Pacman USB_TEST_SERIAL, Android 16, SELinux Enforcing, ADB UID 2000,
the probe ran as Android UID 10225 in untrusted_app, extracted Fedora successfully
and returned Fedora 44 with exit 0. Guest uid=0 is emulated; it is not Android
root. See evidence/stock-probe-pacman.log. The bootloader state is orange, so this
is not an untouched/locked stock acceptance device. No device credential,
debugging mode, SELinux policy or child-process restriction was changed.

PRoot components currently come from official Termux packages, with HTTPS
repository hashes and the required libtalloc SONAME adjustment recorded in
evidence/proot-staging.json. They are now staged into the main application for
integration testing, but are not release-cleared. Repository
signature verification, a source-reproducible build, full license packaging and
16 KiB device validation remain release requirements.

## Unfinished acceptance

Tier 0 startup/backend integration and all three installation routes have device
evidence. App-private Fedora networking, package installation, Git and Java also
passed on Edge 40. The entire GUI and debug APK were built in app-UID Fedora
from source 940bc9b; see SELF-BUILD.md. AndroidDiagnosticsBridge now exposes
read-only Stock/Developer/Root inspection to the Fedora agent through a
same-UID Unix socket. Both devices passed actual bridge calls; foreign UIDs
were rejected. Android-to-Fedora processing and Android readback also passed.
Remaining: phone-built APK self-update, wireless pairing, arbitrary Android
administration commands and their process cancellation, legacy data migration,
private-provider/OAuth acceptance, and release-signed clean installation on an unchanged
stock device. Direct privileged PackageInstaller success requires a separately
provisioned ROM integration; its ordinary-app denial has been verified.
Root ADB on the remote Edge 40 has not been disabled yet. The independent Pacman
test establishes app-UID execution without risking the sole remote connection.

Actual opencode/big-pickle inference has now passed Android/Fedora diagnostics
and a real C failure/edit/rebuild/test cycle. Latest v11 installation results
are 3/3 for each route. See INTEGRATION-V10-20260908.md for scope and evidence.

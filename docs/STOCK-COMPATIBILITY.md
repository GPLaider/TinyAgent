# Stock startup compatibility correction

Stock Android must run Fedora/OpenCode without ADB, developer options or root.
ADB is only an optional Android administration capability, never a prerequisite
for the local Linux environment or provider authentication.

The user's stock Galaxy Z Flip7 failed while PRoot executed `/system/bin/tar`
with `Operation not permitted`. PRoot suggested PROOT_NO_SECCOMP=1. The shipped
runtime had omitted that compatibility setting. Its diagnostic is a hint, not
proof that this is the only cause on the affected kernel.

The shared production PRoot builder now sets PROOT_NO_SECCOMP=1 for extraction,
version checks and backend launch. This disables PRoot's optional acceleration;
it does not disable Android seccomp, SELinux or the app sandbox. The debug probe
also uses it and extracts into a new isolated test directory.

ADB error text now explicitly says the connection is optional and separate from
Fedora. Root guidance is shown only when root was selected. Fedora and Android
connection diagnostics have separate headings. All three callers no longer
invent port 5555 when no connection port was configured. Existing explicitly
stored settings are retained.

v18+ adds wireless pairing/TLS with separately discovered pairing and connection
ports. Dadb remains the explicit legacy/root TCP transport. The wireless route
uses pinned LibADB Android BC source. See WIRELESS-DEVELOPER.md for onboarding
and actual verification results.

## Evidence and limits

- Before change, an actual running app-owned PRoot process failed the check for
  PROOT_NO_SECCOMP=1. After change, the real process environment passed.
- With TCP adbd disabled (service.adb.tcp.port=0), the diagnostic extracted a fresh
  Fedora directory and ran Fedora identification commands as app UID 10225 under
  SELinux Enforcing. The regular backend also executed a Fedora command.
- The test phone is custom-ROM Pacman, not the affected Flip7. Host USB ADB was
  used to observe/start the test; the app does not use ADB to run Fedora.
- Android build/lint, packaged inputs and 99 Java policy checks passed.
- Flip7 was not operated because the user reserved it for personal use.
  Lyriq/Pacman app-UID checks prove the tested no-self-ADB execution path;
  they do not establish compatibility with every stock vendor kernel.

## Lyriq 1 first-install follow-up

On 2026-09-08, v16 was first installed on Lyriq 1 (ZY22J58799). The native
Prepare button unpacked Fedora and started OpenCode under Android UID 10000,
SELinux Enforcing, with Root unchecked and no optional ADB connection configured.
The actual WebView loaded the empty session list. Authenticated local API health,
the six harness paths, Fedora 44 identity and guest identity worked across three
sessions. Guest UID 0 is PRoot emulation; the Android processes stayed UID 10000.

The same check exposed missing `/usr/bin/git`. OpenCode's shell API reported
`completed` even for that command failure, so completion alone is not treated
as success. The test now validates expected command output. v17 adds missing
Git/Python/make/GCC/unzip installation to the shared preparation path, including
repair of existing installations. Network installation errors remain visible
and retryable through Prepare. v17 and v19 passed Fedora identity and Git commands
in three sessions; the earlier sessions survived the updates. v17 also passed
three session-open/Android-back cycles and a force-stop/relaunch recovery.

Lyriq 1 denies `run-as` with `setegid(AID_PACKAGE_INFO): Operation not permitted`.
The private-file test now checks observer access before any UI action; it must
not interpret access denial as file absence. UI/process evidence and the real
WebView API are used instead. This is custom-ROM verification, not a Flip7 result.

Install the compatibility preview as an update, leave optional ADB settings
alone, and select Environment preparation. Do not clear application data.

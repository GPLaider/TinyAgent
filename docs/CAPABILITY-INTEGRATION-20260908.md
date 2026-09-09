# Capability integration — 2026-09-08

These are development builds, not a completed release.

## Reproduced failures and fixes

- Root was a prerequisite for preparation and conversation entry. The default
  runtime now belongs to the application UID, under files/linux. Android
  administration is an independent, explicitly selected capability.
- No active DNS prevented an offline local backend from starting. Preparation
  now continues offline; Android LinkProperties refresh DNS on reconnection.
- Android API 30 lint caught unguarded API 31/33 calls in the new installer.
  Version guards and buffered stream copying fixed all three build errors.
- Stopping PRoot with Process.destroy() left it alive: its TERM signal is ignored.
  Killing only PRoot orphaned OpenCode. A fixed launch script records the owned
  PID; the app validates its UID and sends QUIT, which invokes PRoot tracee cleanup.
  Three repeated real UI stops verified both PRoot and OpenCode disappeared.
- Full APK streaming to Edge 40 stalled near 23%. A lossless 226205-byte delta
  reconstructed the 128356753-byte APK on the phone. Both sides verified SHA256.
  This transfers host-built bytes; it is explicitly not phone build evidence.

## Installation route acceptance

APK: `tinyagent-capabilities-v2.apk`, version `0.1.0-dev`, debug signature.
SHA256: `a7d10b7149567f0bcbb48af492bc07e1515ba700096d2de9616deed4848ce495`.

| Route | Device | Actual mechanism | Result |
| --- | --- | --- | --- |
| Stock | Pacman 000501423003390 | PackageInstaller session and Android approval dialog | 3 consecutive successes |
| Developer | Pacman 000501423003390 | App self-ADB, loopback nonce, UID 2000, streaming package install | 3 consecutive successes |
| Root | Edge 40 ZY22HZPLL8 | App self-ADB, private nonce, UID 0, streaming package install | 3 consecutive successes |

Fixture package: `io.github.gplaider.tinyagent.installfixture`.
Installed SHA256: `1b5480033cf4197db93a4c743f8e96e046caa08fc0d70fc77039fb84d00002ee`.
The first stock cancellation returned STATUS_FAILURE_ABORTED without installing;
selecting the APK again and approving the native dialog succeeded.

Evidence: `evidence/install-stock-000501423003390.json`,
`evidence/install-developer-000501423003390.json`,
`evidence/install-root-ZY22HZPLL8.json`, `evidence/stock-install-confirm.xml`.
Runnable fixture and UI checks: `build-install-fixture.py`, `check-install-route.py`.

Pacman's Developer test enabled legacy TCP ADB on 5555 through the existing USB
development connection. It does not demonstrate wireless pairing. Both devices
run custom ROMs; neither is a clean, bootloader-locked stock acceptance target.
On Pacman, direct ROM installation was rejected because the APK lacks the actual
INSTALL_PACKAGES grant. No ROM privileges were manufactured to make it pass.

Capabilities-v4 SHA256:
`cd05d7b6fbfdb0ba72e2ad1122e136d2f22bb84f2b93c8105708f1c69303fe91`.
The installer now preserves the last used route and rejects a second request
while the original PackageInstaller session awaits its result. On Pacman, Stock
and Developer again passed three consecutive installs; their current evidence
files record v4 (the v2 records are retained in commit 940bc9b). The actual duplicate-request
test preserved the original session and then approved it successfully; see
`evidence/install-pending-guard.json` and `scripts/check-install-pending.py`.
Android 11 privileged installs cannot force user action, so that combination is
explicitly rejected on the Stock route. The API-level guard passed lint but was
not tested on a privileged Android 11 device.
Host assembleDebug, lintDebug, 92 policy checks and packaged native/GUI/runtime
hash verification passed. The prior Fedora session and harness configuration
were still readable from the actual v4 backend after updating Pacman.

## Runtime and persistence

Capabilities-v3 SHA256:
`14511fad9f6232b088f37e4525eaa7bdc47dfcda236c755dd3b021a60f157a6e`.
On Pacman, native UI start/stop passed three consecutive cycles, followed by
force-stop/reopen with automatic runtime startup. See `evidence/stock-restart.json`
and `scripts/check-stock-restart.py`. This is not a claim that all seven release
journeys passed three times.

The actual OpenCode API executed Fedora cat under the app-owned backend and
saved its result in session `ses_f7fbf2c60ffevZKGUZWL5viUMT`. After APK updates and
backend restarts, that same session still returned the recorded Fedora output.
The v3 backend's actual config contained both fixed and measured harness paths.
No inference occurred: this was the user-triggered shell API, with zero model tokens.

On Edge 40, the new backend and PRoot run as Android UID 10151 on 4097; the older
root backend remains separate on 4096. The new backend executed package setup,
Git 2.55.0, Python 3.14.7 and Temurin Java/javac 17.0.20.1 under app UID.
`evidence/edge40-stock-build-tools.json` records the actual session result.
Pinned SDK input downloads and ARM64 AAPT2 version execution also passed;
see `edge40-stock-sdk-inputs.json` and `edge40-stock-sdk-config.json`.

## Remaining

Phone source/GUI/APK self-build passed on app-UID Fedora; see SELF-BUILD.md and
`edge40-stock-self-build-copy-clean-cache.json`. This was source 940bc9b, with a
new phone debug signing identity, not a completed signed update.

Remaining: signed state-preserving self-update; provider/OAuth inference;
arbitrary agent-callable Android shell tools; legacy root session/workspace migration; wireless
pairing; clean stock release installation; complete dependency licenses/source
provenance; and all seven full release journeys with sustained resource checks.

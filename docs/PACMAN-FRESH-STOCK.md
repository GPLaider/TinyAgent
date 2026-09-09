# Pacman fresh Stock check — 2026-09-08

User authorized uninstall/reinstall on Pacman if virtual Pixel was impractical.
Local SDK has emulator executable but no configured AVD/system image. Current
APK packages arm64-v8a only. No emulator was booted; no virtual Pixel pass claimed.

Target: 000501423003390, Nothing A142/Pacman, Android 16,
Nothing/Pacman/Pacman:16/BP2A.250605.031.A3/2606091925:user/release-keys,
SELinux Enforcing. Flip7 untouched.

Force-stopped and uninstalled only io.github.gplaider.tinyagent.debug, then
installed the unchanged published preview2/v20 artifact:
0cfbd92efea5445df2d9ddedd1491f84d7a01151b4a3b48c184248cb4d405f3d.
New app UID 10227 (previous UID10225). Started through AppActivity, pressed
Prepare, allowed notifications. No Developer pairing, root, or app ADB endpoint.

Fresh extraction completed (prepared-v1 exists). Fedora microdnf ran but failed
resolving mirrors.fedoraproject.org. Android also could not resolve the hostname;
ConnectivityService reported Active default network: none. This does NOT
reproduce Samsung's PRoot execve(/system/bin/tar) EPERM. No Fedora/backend success
is claimed. Wi-Fi enabled to attempt reconnection; still no active default network.

Evidence: evidence/pacman-v20-ui-setup.json and pacman-v20-network.json.
Observer now accepts optional pacman target; WebView check supports fresh Stock
expectations but has not run because preparation has not completed.

Next: connect Pacman to internet, press Prepare again, observe with
scripts/observe-lyriq1-setup.py v20 pacman; then check real local WebView/Fedora.
Initial offline UX currently exposes long package-manager DNS errors instead of
a concise network-required recovery action. Application source unchanged here.

## Wi-Fi retry and screen-off verification

User authorized connecting the guest Wi-Fi. Connected through Android Settings;
Android DNS resolved Fedora mirrors and Fedora received the network DNS servers.
Pressed Prepare again without resetting app data. Package installation completed,
then app-owned PRoot/OpenCode started as UID10227. Fresh Stock setup passed.
The successful observation is now in evidence/pacman-v20-ui-setup.json; original
offline error remains in evidence/pacman-v20-network.json.

Screen-off test passed 3/3: Home, screen off for 15 seconds, confirm Android
Asleep/Dozing, backend health, execute Fedora sha256sum /usr/bin/git while off,
verify three saved sessions, wake and return. See
evidence/pacman-screen-recovery-v20.json. USB stayed connected. This does not
prove long Doze, unplugged CPU suspension, or credential-locked recovery.
Runtime uses foreground service but currently has no partial wakelock.

Real authenticated WebView checks passed: three sessions executed Fedora release,
guest id, and Git 2.55.0; all six harness instruction files configured. Android
bridge measured app UID10227, selected_transport=stock, root_selected=false;
Developer access was rejected. Evidence: pacman-v20-webview.json. No provider
or model inference and no full APK self-build in this check. Temporary host ADB
forwards 14097 and 19222 removed; app remains running on Pacman with Wi-Fi on.

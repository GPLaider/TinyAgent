# Remaining validation pass — 2026-09-08

This is development validation, not completed release acceptance.

## Executed

| APK/device | Actual check | Result/evidence |
|---|---|---|
| v12/Pacman | Native runtime start/stop, force-stop/reopen | 3/3; `stock-restart.json` |
| v12/Edge 40 | Abort long command, verify exact process gone, retain session/health | 3/3, 3.58–4.12 seconds including ADB measurement overhead; `job-abort-v12.json` |
| v12/Pacman | Five-second screen off/on, background/foreground, three stored sessions | 3/3; `screen-recovery-v12.json`; no long Doze or credential-lock claim |
| v12/both | Stock/Developer/Root measured UID, rejected wrong authority and foreign socket UID | passed; `android-bridge-integration-*.json` |
| v12/Edge 40 | Android root inspection → Fedora JSON processing → Android readback | exit 0; `v12-android-fedora-exchange.json` |
| v12/Edge 40 | Fresh big-pickle agent reads harness, inspects Android, creates failing Python test, edits source, passes same test | passed; `v12-agent-regression-1.json`; exact harness/identity reads approved once |
| v12/Edge 40 | Independently rerun generated Python test | passed; `v12-agent-independent-test.json` |
| v12/Pacman | Settings navigation, custom provider input, IME Back | passed; `v12-settings-regression-1/result.json`; no credential save/inference claim |
| v14/Pacman | New draft, stored session open, Android Back to home | each 3/3; `mobile-workspace-v14/result.json` |
| v14/Pacman | Settings navigation, custom provider input, IME Back after final GUI fix | passed; `v14-settings-regression/result.json` |
| v14/Edge 40 | Host-built update, exact installed hash, retained agent session and generated Python test | passed; `v14-edge-installed.json`, `v14-preserved-agent-session.json`, `v14-preserved-workspace-test.json` |

v12 host SHA256: b3f24ce94096cc75cd0d6b8410b6e945938149aa696005fcdfee1b277502a285.
v12 phone SHA256: abd22ba4fb37a0150138df2b3b2c7e85cbeebd4cd16a725831391e63d3b607a0.
v14 host SHA256: b59bd21ffbab819f3d6b88e545b0327bf1d6a43443fe28659e10b77d8087377a.
Development certificate: a3ef78ae0bfdfc30307e3448e138eca29adf39d966f89af116bbce151abc1ed2.
Version remains 0.1.0-dev / code 1; v12/v14 name local test artifacts, not release versions.

## Failure repaired during validation

v12 with no registered GUI project showed an empty home despite backend sessions.
The top New Session action returned without doing anything because every project
fallback was empty. TinyAgent now identifies its WebView with a User-Agent suffix;
its local 127.0.0.1 home registers the existing /workspace when no project is open.
It does not create a repository or change remote OpenCode projects.
v13 reproduced recovery of the list and draft creation. v14 also removes the
clipped duplicate mobile New Session action and hides tooltip shortcut badges on
touch devices. Actual Android WebView validation uses installed Playwright via
CDP because Browser plugin is unavailable. UIAutomator still supplies Android Back.
The v14 screenshot was visually reviewed: duplicate clipped action is gone and
the Home tooltip contains its label without Ctrl-B. CDP forwarding was removed
after the check. Edge v14 is host-built; the separately retained v12 artifact
remains the verified phone self-build/update result.

Host GUI production build, TypeScript check, Android assemble/lint and all packaged
runtime/native/license/952 GUI asset checks passed. Java policy checks: 99 passed.
The first v14 UI-runner attempt assumed the screen started on a draft; it toggled
away from an already-open home and timed out. The runner now observes the initial
screen before clicking Home; the same workflow then passed three times.

## Gates that cannot be marked passed

- Personal OpenAI OAuth: connected provider inventory still contained only
  opencode. Owner login was requested; no credentials were copied or fabricated.
- Clean stock first-install: all available test phones use custom/unlocked ROMs.
  App-UID/SELinux checks do not substitute for a clean stock device.
- Network handover: USB Pacman had Wi-Fi enabled but disconnected. No connected
  alternate path was verified; no network-handover pass is claimed.
- Privileged ROM PackageManager success: ordinary app permission-denial checks
  exist; no INSTALL_PACKAGES-granted build was tested.
- Arbitrary Android commands, wireless pairing and Shizuku are not implemented.
- Production signing, full provider/auth-refresh/custom-endpoint acceptance,
  Korean composition, long conversations/scroll, long Doze/resource soak and
  three complete seven-journey release rounds remain open.

These are explicit release blockers. Component 3/3 results above are not three
complete release rounds. APKs remain development builds.

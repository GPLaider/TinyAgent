# Focused onboarding, signing and theme revision

Harness v6 includes STOCK.md, ADB.md and ROOT.md in every new/resumed OpenCode
context, alongside common instructions and live measurements. These are
capability guides, not permission grants. They explain actual current tools,
UID boundaries, workspace/exchange paths, installer choices and recovery.
Arbitrary Android command execution and wireless pairing are still unimplemented
and are explicitly marked unavailable rather than implied by the guides.

System appearance now uses Android values/values-night resources. Native setup,
installer and dialogs inherit the matching light/dark theme; hardcoded setup
colors were replaced. OpenCode already defaults to system color scheme and
subscribes to prefers-color-scheme changes. Explicit user theme choices remain
respected. Configuration changes recreate the Activity through Android's normal
saved-state path.

For the currently installed debug stream, host and phone now share the existing
development certificate a3ef78ae0bfdfc30307e3448e138eca29adf39d966f89af116bbce151abc1ed2.
The user requested matching signatures. `provision-development-signing.py`
checks the exact device and certificate before transferring the development
key directly into app-private storage. Private material never enters Git,
APK assets, /sdcard, shared ADB staging or logs. Existing differing target
identities are rejected. The old phone-generated debug key is preserved.

Phone builds require `/root/.tinyagent/signing/development.properties` or the
explicit TINYAGENT_SIGNING_PROPERTIES path. If absent, the build fails instead
of silently generating a different update identity. Gradle reads the private
configuration; release signing remains separate and unset. This development
certificate is not a production/release identity.

Reproduce provisioning with:
`python scripts/provision-development-signing.py --serial 100.79.65.42:5555`.
Then run `scripts/build-android-fedora.sh` inside the phone source checkout.

## Verified on 2026-09-08

- Source 24666a4d1c625ecbd140648e333b7a079e51d944 rebuilt on Edge 40
  ZY22HZPLL8 inside app-managed Fedora in 2m39s. The existing phone-compiled
  GUI was reused. Packaged harness, bootstrap, native, notice, 952 GUI asset
  and runtime archive checks all passed.
- Phone APK SHA256:
  abd22ba4fb37a0150138df2b3b2c7e85cbeebd4cd16a725831391e63d3b607a0.
  apksigner verified certificate a3ef78ae0bfdfc30307e3448e138eca29adf39d966f89af116bbce151abc1ed2.
  The exact phone output updated the installed v11 APK successfully with no
  uninstall or host re-signing. Private backend credential and C source hashes
  were unchanged. The previous model session was readable after restart and
  `make clean test` passed again in its preserved workspace.
- Actual v12 backend configuration loaded all six instruction files, including
  STOCK/ADB/ROOT. This proves configuration and packaging, not new model inference.
- Pacman 000501423003390: native light/dark and OpenCode dark/light screenshots
  were visually reviewed. Both followed system appearance. Initial system mode
  `no` was restored. Host APK SHA256:
  b3f24ce94096cc75cd0d6b8410b6e945938149aa696005fcdfee1b277502a285.
- Evidence: `evidence/edge40-v12-*.json`, `evidence/system-theme-v12/result.json`.
  Runnable focused update check: `scripts/check-phone-signed-update.py`.

Still pending: clean stock-device acceptance, arbitrary Android commands,
wireless pairing/Shizuku, production signing, private OpenAI OAuth and complete
release regression. This focused revision does not close those gates.

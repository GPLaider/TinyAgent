# GUI production channel — Lyriq1 update

Vite's OpenCode channel defaults to dev independently of a production Vite
build. The phone self-build now passes `OPENCODE_CHANNEL=prod`; the desktop
GUI candidate was built with the same environment value. No desktop tab
behavior was changed.

Candidate: TinyAgent-gui-prod-channel.apk, 130208297 bytes, SHA-256
`5c9f27b0579e0566606f2017bb4d85f00925f3667e62f21004b48c3b54c150af`.
Existing development signer: `a3ef78ae0bfdfc30307e3448e138eca29adf39d966f89af116bbce151abc1ed2`.
This is a debug-package candidate with a production GUI channel, not a
production-signed release.

Clean assembleDebug and lintDebug passed. Packaged native/runtime/harness
and 952 GUI asset checks passed. Exact APK reconstructed and SHA-256 verified
on ZY22J58799, then pm install -r returned Success. No data clearing occurred.
Before/after API snapshots retained all 42 session IDs, connected provider IDs
openai and opencode, and dark theme. This verifies retained provider connection
state; it is not a fresh post-update OAuth inference test.

Subsequent post-update inference in `ses_f757ff0cbffejCE8JF1NGpTVk3` used
the retained OpenAI OAuth and gpt-5.6-luna. Four bash calls completed with exit
0: startup recovery flag absent, /workspace, aarch64, Fedora release 44.
The assistant returned a final answer and the session became idle.
Transcript: `evidence/ses_f757ff0cbffejCE8JF1NGpTVk3-probe.json`.

Evidence: gui-prod-channel-install-before.json,
gui-prod-channel-install-after.json, lyriq1-gui-prod-channel-after.png.
The real WebView screenshot no longer displays the DEV badge. Crowded bottom
tabs remain visible and unresolved. Native showWeb reuses the existing WebView;
it does not reload the root route on every return from settings.

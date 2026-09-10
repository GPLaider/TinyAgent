# Approval policy display — 2026-09-10

The session permission API accepted a single `*/* allow` rule, but TinyAgent displayed Basic because its UI required an explicit external_directory allow rule. A browser regression reproduced expected `yolo`, actual `basic`, timing out after 10 seconds.

The UI now honors the last blanket rule, recognizes fully allowed policies and its own Basic/Read presets, and labels other policies Custom. Deny rules, pattern restrictions and doom-loop exceptions cannot masquerade as YOLO. Unknown equivalent custom rule arrangements are conservatively labeled Custom; this label never rewrites their rules. Loading is shown until the backend policy arrives. Outdated requests cannot overwrite a later mode change.

Validation before packaging:

- `tinyagent-access.test.ts`: 10 assertions passed, including deny ordering and every built-in preset.
- Browser regression: full-access and custom-restriction displays each passed three times (6 passed, 16.6 seconds). Merely displaying them issued no session PATCH or permission reply.
- One test instrumentation failure counted unrelated project PATCH requests. The observer was corrected to track session policy/reply writes; production behavior was not changed to suppress project requests.
- App and E2E type checks passed.
- Production cold/hot session-switch benchmark passed before and after, five trials per mode. Median first-correct cold 17.0 → 15.4 ms; stable cold 45.0 → 39.6 ms; first-correct hot 3.0 → 3.0 ms; stable hot 26.8 → 27.0 ms. No wrong, blank, or unknown destination samples. This is a small host fixture check, not evidence of a device performance improvement.
- Packaging uses a separate normal production GUI build, not the benchmark server's port configuration.

Pending: install/readback on Lyriq1, actual mode changes and persistence, native picker touches, and regression of actual approval requests. Existing OAuth and sessions must remain intact. This is not the complete prerelease acceptance gate.

## Device update and policy persistence

Installed `TinyAgent-access-policy-b85b8f60.apk` on Lyriq1 ZY22J58799. SHA-256 `b85b8f60c57de362e26ef828e8071f86e4eea6d4d1ee61d420dc4b807c6aed6a`, 141583365 bytes, retained development signer a3ef78ae… . Debug build/lint passed in 17 seconds; packaged-runtime and GUI hash checks passed. Before/after snapshots `lyriq1-access-policy-{before,after}.json` preserved all 33 sessions, connected OpenAI/OpenCode providers, and dark theme.

In the dedicated QA session `ses_f761a8a35ffevxs65Wf07SNgIr`, the actual WebView select change handler was exercised through Basic → Read → YOLO three times. All nine transitions saved the expected policy to the real backend and restored the correct display after navigation. Evidence: `lyriq1-access-policy-rounds.json`. This was synthetic DOM change input, not native picker touch. `lyriq1-access-policy-b85b8f60.png` was visually inspected and shows YOLO for the API-created allow-all session.

The initial cleanup check failed because it expected byte-for-byte replacement of the rules array. Source inspection of `packages/opencode/src/server/routes/instance/httpapi/handlers/session.ts` confirmed that PATCH uses `Permission.merge(current.permission, payload.permission)`, appending rather than replacing rules. The original effective allow-all policy is restored by its final blanket rule; 65 historical rules remain in this QA session. A subsequent live restoration audit verified this and was appended to the evidence without erasing the failed exact-history check. The helper now distinguishes effective-policy restoration from exact-history restoration. No direct database rewrite was performed.

Native picker touches and actual pending-approval regression remain open. Display/persistence success alone does not prove the complete permissions or release gate.

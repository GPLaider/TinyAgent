# Session reconnect recovery — 2026-09-10

Scope: host browser reproduction of the stale-final-answer symptom observed on Lyriq1. This is not yet installed-device acceptance.

The V1 event stream reconnects without replaying missed message events. `server-sync.tsx` previously fetched active sessions on `server.connected` only when its query cache was empty, and seeded statuses only when no cached value existed. Directory refresh uses `sessionContent: false`; it therefore did not recover the mounted conversation's final message.

Regression: `packages/app/e2e/regression/session-reconnect.spec.ts` loads a busy conversation, changes the server-side final message without emitting message events, then waits for a verified new SSE connection. Before the change the final answer remained absent for the 10-second assertion timeout. After the change the final answer appears without route navigation: one initial pass and three consecutive passes (13.8 seconds for the repeated run).

The fix refreshes the active-session snapshot on reconnection and reuses the bounded session message cache's existing forced sync/merge. Missing formerly active IDs become idle. Status changes received during the snapshot request are preserved, including a new busy event whose value matches the old busy state. No draft reset, reload, new polling loop, or backend restart is introduced.

Validation:

- App typecheck and E2E typecheck passed. A missing test event ID was caught by typecheck and corrected.
- `server-sync.test.ts`, `server-session.test.ts`, `server-sdk.test.ts`: 96 passed, 0 failed; 177 assertions.
- Existing production `session-tab-switch-benchmark.spec.ts`, cold/hot test, five runs each, passed before and after. Chrome fixture measurement on Windows, not device latency.

| Median milliseconds | Before | After |
| --- | ---: | ---: |
| Cold first correct destination | 19.7 | 18.8 |
| Cold stable destination | 43.4 | 45.5 |
| Hot first correct destination | 3.2 | 3.1 |
| Hot stable destination | 24.8 | 25.5 |

All ten switch trials in each benchmark reported zero wrong-destination, blank, or unknown samples. These small runs do not establish a performance improvement. The first benchmark launch failed because the default Playwright browser cache was absent; the successful runs used the existing `D:/TinyAgent-work/playwright` cache.

Pending: native activity return when SSE has not disconnected, retained draft/scroll device checks, network recovery, and actual Lyriq1 OAuth/Luna repeated verification on the newly packaged APK. Do not count these host tests toward the seven-journey device release gate. Lyriq2 and device credentials were not touched.

Packaged candidate: `D:/TinyAgent-work/artifacts/TinyAgent-reconnect-8f39db6f.apk`, 141583220 bytes, SHA-256 `8f39db6fddd6dd6062515e3935f8b9ff5629a3a7e915161a2376fbb22ef94170`. Debug build and lint passed (18 seconds). Packaged-runtime verifier passed all harness/bootstrap/native/license/archive checks and 952 GUI asset hashes. The full retained OpenCode mobile patch was regenerated and reverse-apply checked. This candidate has not been installed or published.

## Subsequent device verification

The preceding installation-pending statement describes the packaging checkpoint. The same exact candidate is now installed on Lyriq1 `ZY22J58799`. Installed base.apk SHA-256 matches. Certificate SHA-256 is the retained development signer `a3ef78ae0bfdfc30307e3448e138eca29adf39d966f89af116bbce151abc1ed2`, not a production signing key.

`lyriq1-reconnect-before.json` / `lyriq1-reconnect-after.json` verify all preceding 30 session IDs, connected providers `openai` / `opencode`, and dark theme were preserved. Actual subsequent OpenAI OAuth model requests succeeded without re-login; token refresh itself was not tested.

`scripts/check-luna-reconnect.mjs` ran three consecutive real-model rounds on that exact APK. It emulates offline networking in the app WebView only, leaving phone-local Fedora/model-provider networking intact. Each model completed one bash call (pwd, uname -m, Fedora release), exit 0, using `openai/gpt-5.6-luna`. Each final message's backend timestamp falls inside the measured offline interval. After restoring WebView connectivity, the mounted conversation displayed the final marker without navigation/reload. Full transcript and tool results are retained in each evidence JSON.

| Round | Session | Offline interval | Result |
| --- | --- | ---: | --- |
| 1 | ses_f761c8923ffeJFNJLZD8DVNQYx | 31,237 ms | pass |
| 2 | ses_f761b8d6cffeVAyvo9Qi7ViFW6 | 30,917 ms | pass |
| 3 | ses_f761a8a35ffevxs65Wf07SNgIr | 30,840 ms | pass |

Evidence: `evidence/lyriq1-luna-reconnect-{1,2,3}.json`, visually inspected `lyriq1-reconnect-round3.png`. Read-only process inspection confirmed app PID15556, PRoot PID15633, OpenCode PID15637 all under app UID10042; SELinux Enforcing.

Video link touch → play → close/reopen also passed three transitions on this candidate: `evidence/lyriq1-video-navigation-8f39db6f.json`. The native menu was dismissed back to the conversation afterward. This does not test model completion while the native video activity covers the WebView.

Remaining scope: actual Wi-Fi/mobile network transitions, native-activity return during model work with an uninterrupted SSE connection, draft/scroll preservation, prolonged background/Doze, full seven journeys. An additional discrepancy is visible in the new API-created QA sessions: the approval control shows “기본” although creation explicitly requested allow-all permissions; investigate displayed mode versus actual backend policy. The bottom DEV/tab bar remains dense. No private prerelease was published in this verification step; Lyriq2 was not operated.

# Lyriq1 Luna UI audit — in progress

## Live continuation after unlock

- Actual taps opened Home → Settings → Providers → Custom provider. OpenAI
  remained connected. Empty submission displayed required-field errors;
  Back returned to Providers. No credential or provider was submitted.
- Settings → Models lists GPT-5.6 Luna from the connected OpenAI catalog.
- A new conversation was created through the visible UI, Korean text was
  inserted through CDP Input.insertText, and the Android Send button was
  tapped. Luna ran `/usr/bin/pwd` and replied in Korean in about 8 seconds.
  This verifies Unicode submission, not physical Hangul IME composition.
- Evidence: `evidence/lyriq1-luna-ui-conversation.json`,
  `evidence/lyriq1-providers-raw.png`,
  `evidence/lyriq1-custom-validation.png`.
- The original Ventoid session continued in parallel. Its first Gradle
  attempt failed on Maven's x86 AAPT2 after 4m10s. Luna selected the included
  ARM64 AAPT2 override and restarted Gradle. Final log: BUILD SUCCESSFUL in
  4m58s, exit 0, testDebugUnitTest and assembleDebug completed. APK size
  23,589,632 bytes, SHA256
  dfc3104160b02f2b4ce237e6c2d8509674e1874777a0971a32c7c96e13058d0f.
  Evidence: `evidence/lyriq1-ventoid-result.json`. APK install/runtime testing
  is outside this build result.
- Actual Stop test: the dedicated Luna session launched sleep 123 as app
  UID10042, PID24304, PPID21141. Android UI Stop was tapped before its natural
  deadline; the process disappeared and the tool recorded User aborted the
  command. The session returned idle. Original Ventoid session was untouched.
- Android Back returned from the QA conversation to the session list. The
  original Ventoid session reopened with Luna/Low and its result intact.
  The phone was left on the original Ventoid conversation.

### Theme flickering: audit-tool defect confirmed

Playwright 1.59.1's `lib/server/page.js` defaults emulated colorScheme to
`light`. Attaching its CDP client changed the real WebView media-query result
to false although Android `cmd uimode night` reported yes. Disconnecting and
querying using plain CDP restored true. Repeated attachments therefore
perturbed a UI using System color mode.

The user selected fixed Dark; it remains saved and applied. Do not change it.
Use `scripts/inspect-webview-theme-raw.mjs` for further live taps, screenshots,
and metadata checks. It sends no Emulation commands and does not restart the
app/backend. Earlier Playwright runs are not valid evidence of system-theme
behavior. The initial theory of an app theme synchronization bug was not
confirmed; the reproducible cause here is the inspection tool.

### Visible issues recorded, not yet patched

- OAuth-backed OpenAI displays a `사용자 지정` source badge, not its login method.
- Bottom navigation Home/add controls measured 28 CSS px high and tab-close
  controls 20 px, below comfortable mobile touch sizes.
- With the optional agent selector shown, Build/Luna/Default compete with
  Send for composer width. Center hit-testing of Send was blocked; an actual
  Android tap farther right succeeded. This needs a responsive-layout fix.
- Settings footer still says OpenCode Desktop.

Target: ZY22J58799, current v26 candidate. Preserve the installed OAuth and
the user's `Ventoid 앱 가져오기 및 빌드` session. No uninstall, authentication
removal, or interruption of the running user task during this audit.

## Verified

- `/provider` reports OpenAI connected and `gpt-5.6-luna` available.
- Existing user conversation contains actual assistant messages with
  `providerID=openai`, `modelID=gpt-5.6-luna`, completed bash/read/glob tools,
  and an ongoing bash tool. This proves model-to-tool integration, not final
  success of the user's Ventoid build.
- The task progressed while the device was at its fingerprint lock screen.
  This is an observed short interval, not a long-duration Doze test.
- No pending permission request at evidence capture.
- Settings V2 uses the upstream `useProviders`, `DialogConnectProvider`,
  server SDK authentication and configuration paths. It is not a separate
  native provider configuration store.

Evidence: `evidence/lyriq1-luna-provider-link.json`; repeat with
`scripts/inspect-luna-provider-link.mjs` after refreshing the target's CDP
forward if its process changes. The script exports only provider/model IDs,
tool status, and connection metadata, never credentials.

## Initial lock-screen limitation (resolved by user)

The device was fingerprint locked. A normal Home click in Playwright timed
out; no forced DOM click was used to claim user-visible success. The user
unlocked it and brought TinyAgent forward. Later automation timeouts also
involved changing UI state and Playwright actionability; they must not all be
attributed to the lock screen.

- Provider connection forms beyond the custom form, endpoint validation, keyboard layout,
  Korean input, scroll restoration, and accessible touch targets.
- Stop/recovery and session switching without disturbing the user's build.
- Provider authentication refresh and additional providers are not tested.

## Source-review follow-up (resolved on d5811e1a)

The backend reports `source=custom` for the existing OpenAI connection. Both
provider settings views now omit a badge for that ambiguous source; an
explicitly configured custom provider still retains its label. The installed
`d5811e1accdb174c5a50450c79931374fd1405e1fe5efd627f193f33113d3863`
candidate displayed OpenAI under connected providers with Luna available and
without the misleading custom badge. No OAuth removal or reconnect was used.

Evidence: `evidence/lyriq1-provider-ui-audit.json` and
`evidence/lyriq1-json-provider-update.json`. The update preserved all 25
preceding session IDs, connected providers and the user's dark theme.

## Current candidate acceptance boundary

On that same candidate, Luna development sessions
`ses_f766b3658ffeNOjH7Q5wjHqFU9` and `ses_f7665db0effexK8HSgTJRcuP0M`
completed an intentional failing test, changed the implementation, then
passed the unchanged three-test suite and Python compilation. Their saved
transcripts and independently retrieved files are checked by
`scripts/check-luna-development-evidence.py`.

The third session, `ses_f7662662bffeLJbDM3NWSzN40L`, is **not counted as a
pass**. A measured 144.179-second Dozing interval retained the app UID's
partial wake lock and backend process. Credential lock after wake prevents
the current WebView observer from retrieving the final model result; user
unlock and comparison of tool timestamps with the interval are still needed.
See `evidence/lyriq1-luna-screenoff.json`. Process survival alone does not prove
that model work completed during screen-off or that long Doze recovery works.

The model-generated JSON path also opened the native action menu and readable
JSON preview on this candidate. This is one observed artifact round, not the
complete image/video, provider-authentication or three-round release gate.

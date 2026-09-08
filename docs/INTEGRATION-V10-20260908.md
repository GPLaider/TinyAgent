# Integration through v11

APK SHA256: `dfe087b883a5b95a0b31f2167058ea211ac96dd114bac4655bc60338da4c582e`.
Debug build, version 0.1.0-dev (1), host debug signer. This is not a release.

The same v10 APK passed three consecutive Stock fixture installs and three
Developer installs on Pacman, and three Root installs on Edge. Exact install
results and fixture hashes are in `evidence/install-*.json`. Privileged-ROM
success is not claimed; ordinary-app denial remains the verified boundary.

## Startup failure and fix

`mobile-settings-v9-pacman/failed-home.png` reproduced immediate conversation
entry failing while the restarted backend was still opening its port. The app
now waits up to 60 seconds for transport readiness while the runtime is wanted;
explicit Stop, recorded setup failure and HTTP/authentication failures do not
become silent retries. Starting the service clears stale Ready status.

v10 opened the actual GUI. The first automated reruns expected Korean labels
but the fresh Pacman GUI used English. After selecting Korean through Settings
and observing the changed screen, the setting survived restart. Pacman's
WebView includes both label and description in input hints; the provider-ID
test now matches the description suffix and still verifies exact focus.

`mobile-settings-v10-pacman-cycle1`, `cycle2`, and `cycle3` each passed:
app restart, GUI entry, mobile shortcut omission, all four settings sections,
provider ID input, keyboard Back, provider/menu Back and close. No credentials
were entered or custom provider submitted. This is three settings passes,
not the full seven release journeys. Host build, lint and all packaged hashes
also passed.

## Actual model and tool execution

Edge's connected catalog exposed zero-cost `opencode/big-pickle`. An actual
inference was asked to inspect Android Stock and Fedora using the harness.
It invoked the live diagnostic socket, then requested
`cat /etc/fedora-release && id && pwd`. OpenCode required external-directory
permission for `/etc`; only that exact pending identity probe was allowed once.
Global automatic approval was not enabled.

Both commands completed. The Korean response distinguished Android app UID
10151 from PRoot's emulated guest UID 0 and reported Fedora 44. The final step
recorded 200 output tokens and cost 0. The complete transcript is
`edge40-actual-model-android-fedora-transcript.json`; the final response is
`edge40-actual-model-android-fedora.json`. This is real inference, not the shell
API test. Personal OpenAI OAuth and Luna are still untested.

## Phone rebuild

The complete GUI and APK build at d3d6392 passed in app-UID Fedora. Its APK is
`tinyagent-phone-d3d6392-debug.apk`, SHA256
`c01db18eb5f5e41731f0738159f0b749f6db635137558a67124c6f1a9e914a29`.
The phone debug v2 signature verified after exact-hash export. This build
precedes v10's native startup retry; see SELF-BUILD.md for the source and logs.

The subsequent native rebuild at `ee914a4` includes v10's startup fix. It ran
inside the same app-UID Fedora and succeeded in 35 seconds (4 tasks executed).
Packaged hash checks all passed. Exported output:
`D:/TinyAgent-work/artifacts/tinyagent-phone-ee914a4-debug.apk`, SHA256
`e449291a43ab3d2a0e666800e93ef87888c5d8f457991771572d919fcc5204c5`.
The unchanged phone debug certificate verified its v2 signature. The GUI was
reused from the preceding full phone build; it was not recompiled for this
native-only change. Reports: `evidence/edge40-v10-*.json` and
`evidence/edge40-v10-phone-signature.log`.

## v11 harness correction and actual development loop

APK SHA256: `8327afb8cd5e673741c45524f524579a1a159c4b04b22d08e2a5955702dc0e7e`.
Native code and GUI are unchanged from v10; the fixed harness is now version 5.
The preceding actual-model test called the development bootstrap despite a task
restriction against network/package operations. Harness v4 had told every first
development task to prepare the toolchain. That instruction was too broad.
The session was aborted; subsequent process inspection found only the app,
PRoot and backend. The transcript shows the bootstrap had already completed,
so this is not proof of terminating it mid-command.

Harness v5 instructs the agent to use existing tools, respect task-specific
network/install restrictions and prepare only missing prerequisites when
allowed. The exact APK harness bytes are now checked by the packaging test.
On Edge, a new actual big-pickle session ran the same development task with
this harness: initial C source 6*6, make test failed with exit 2, actual edit to
6*7, clean rebuild/test passed with exit 0, executable output 42. All tool
commands were inspected: no bootstrap or network/package command was invoked.
An independent make clean/test also passed. The LLM itself used its configured
remote provider, as designed.

Evidence: `edge40-actual-model-development-v11.json`,
`edge40-model-development-independent-check.json`; failed prior attempt:
`edge40-model-development-aborted.json`. This is actual inference and file
editing/building on the phone, not an assistant-written result fixture.

v11 host build/lint and all asset hashes passed. Stock, Developer and Root
installation each passed three times on this same APK; see the route reports.
Formal release, private-provider OAuth, clean stock hardware, ROM-privileged
success and installation of the phone-signed output remain open gates.

The phone then rebuilt source `11e81854c40f78ee3cef75815f498e05427cb37e`,
including harness v5, in 1m31s (3 tasks executed). All packaged checks passed
inside Fedora. The exported APK's complete SHA256 is
`c209e9b39f3f114fd7daf7acdcb7ada0e4b9a1d9b2bc63ffc4cafc7e549cc0b0`:
`D:/TinyAgent-work/artifacts/tinyagent-phone-11e8185-debug.apk`.
Its phone debug v2 signature verified. The preceding actual-model conversation
remained readable after app updates; no permission request remained pending.
Evidence: `edge40-v11-*.json` and `edge40-v11-phone-signature.log`.

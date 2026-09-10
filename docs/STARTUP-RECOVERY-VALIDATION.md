# Startup recovery — source candidate, not deployed

## Real failure, Lyriq1 2026-09-10

Installed APK `69a6b1a1a357ed0fb7eb9b7508dd800987ce916d803df86cef463c5ad14d95b6`
uses the fixed PRoot but OpenCode tinyagent.1. A dedicated user-shell probe
session `ses_f75abc97cffeJ45xl4epWGj3AO` ran `/usr/bin/sleep 180`.
This was a direct tool API test, not an inference; its stored default model
label must not be described as a Luna model run.

Before stop: app 26977 → PRoot 27130 → OpenCode 27138 → bash 27571 → sleep 27597,
all Android UID 10042. The visible native Work Environment → diagnostics →
Stop button terminated every child; ps showed only the app afterward.
Prepare restarted the backend. Readback then showed session idle but tool
still running. Evidence: `native-stop-recovery-before.json` and
`native-stop-recovery-failed-after.json`.

The probe alone was subsequently cleaned with the existing abort API, after
checking it contained exactly one sleep command. Readback showed tool error,
interrupted=true and assistant MessageAbortedError. This manual cleanup is
not evidence that automatic startup recovery is deployed or passing.

## Source fix and host evidence

`src/session/startup-recovery.ts` executes before `serve` binds its HTTP port,
only when the native caller sets TINYAGENT_PREVIOUS_RUNTIME_STOPPED=1. The CLI
consumes/removes that signal so model-launched child servers do not inherit it.
The caller must have confirmed termination of the previous owned process tree;
it is not a general maintenance operation for a live/shared database.

One transaction marks unfinished assistants and pending/running tools as
interrupted. Completed tools and completed history are preserved; existing
inputs, partial output, metadata and start time remain. Repeated recovery
does not rewrite already finalized rows. No HTTP clients exist at this stage,
so there is no cancellation race with a newly submitted turn.

The new actual database test first failed with expected error, received running.
After implementation it passed, including pending tools, partial output,
completed-history preservation, interrupted-before-tool and idempotency.
Selected regression run: 5 passes, 30 assertions, no failures; typecheck passed.

## ARM64 candidate and remaining work

`runtime/opencode-runtime-recovery-2.json` and its immutable patch identify
version 1.18.29-tinyagent.2, binary SHA256
`c92991c178f77ec717f64def66c01a6bcb93ea834be1c5a50b7be0649fb9f20e`.
Verified packaged archive SHA256:
`5139469d4fa9b7371129a956765d7ede425232c4d6bdbb07ab86f966c56fe2a2`.
Previous binary/manifest/archive are preserved. This candidate also contains
the previously source-tested direct-shell exit-code fix.

Not deployed: native startup flag wiring, new runtime asset/hash promotion,
ARM runtime execution and three real stop/restart rounds. The phone still uses
tinyagent.1. Preserve OAuth/sessions/workspace and keep Lyriq2 untouched while
performing those remaining steps. Full release acceptance remains open.

## Native integration and clean APK candidate

Native wiring now refuses startBackend before successful prior-process recovery,
then sends the consumed startup flag. Main runtime assets/hash checks and phone
self-build packaging default now use tinyagent.2. The legacy root runtime is
versioned 0.1.2 for the new archive, without enabling startup recovery there;
that transport has not received the required process-ownership validation.

An incremental Gradle APK retained 49,970,631 bytes outside referenced ZIP entry
payloads, inflating it to 180,006,460 bytes. A clean rebuild produced 130,208,293
bytes with the same verified functional assets. The package verifier now rejects
more than 4 MiB of non-payload overhead for this app; the oversized candidate
failed and the clean candidate passed. Phone build-android-fedora.sh now cleans
before packaging as well. Clean assembleDebug/lintDebug passed.

Clean APK SHA256:
`f980ef990becc07fd1a36f363d3578b950039ae2b6f7121db0ddbe0e123df2a7`.
Same development signer. The 180 MB candidate is retained only as failure
evidence and must not be distributed. Device transfer/installation validation
was pending when this entry was written.

## Installed and real recovery passed

The clean APK above is now installed on Lyriq1; installed base.apk SHA256
matched. Backend health reports `1.18.29-tinyagent.2`. Initial and final
startup-recovery-2 snapshots retain all 36 pre-update session IDs, provider
connection IDs openai/opencode and dark theme. After four dedicated recovery
probes there are 40 sessions; no prior session was deleted.

The first automated attempt hit a moving preparation-layout control before
opening the conversation. Its backend recovery passed when read back, but it
was not counted in the consecutive run. Its before/after evidence is retained
as native-recovery-layout-attempt-*.json. The test now waits for preparation
to settle before collapsing diagnostics.

`scripts/check-native-stop-recovery.py` then passed 3 consecutive rounds:

- ses_f75990353ffeKVI9Cnr4GK7lCs
- ses_f75982fa8ffeAlxmXkTWd1B8Ux
- ses_f759743b9ffeq52Nrmhm8dkVtQ

Each started a real sleep child, observed the app-owned process chain, used
the native Stop button, verified ps contained only the app, used Prepare, and
read back idle session + error tool + interrupted=true + recovery=runtime-restarted.
No manual abort was used to pass these rounds. Full process snapshots and
results are in lyriq1-native-stop-recovery-rounds.json with per-round transcript
files. Final live chain: app 29306 → PRoot 31230 → OpenCode 31237, UID 10042.

An additional existing-OAuth Luna check was started in
ses_f7595e550ffeB033viJAx1GWSv to inspect Fedora and ensure the consumed startup
signal is absent from model-launched tools. Its result is pending at this entry.
These direct-tool restart rounds do not prove every interrupted model-stream,
network-change, update or screen-lock journey. Those release gates remain open.

The additional OAuth/Luna check finished idle and succeeded: its actual bash
tool exited 0, printed RECOVERY_FLAG=ABSENT, /workspace, aarch64 and Fedora 44.
This verifies the startup signal was consumed rather than inherited by tools.
Evidence: ses_f7595e550ffeB033viJAx1GWSv-probe.json. Existing OAuth was reused;
credentials were not read into the report or replaced.

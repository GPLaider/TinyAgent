# DeepSeek 4.1 Flash phone build observations

Campaign starts only after actual dnfast 43b0928 check/refresh/install/run passed
on all three phones. Submission receipts under evidence/go-campaign bind the
model, hardware serial, APK hash and baseline source revision. Historical APKs
do not count. The supervisor has not built these apps for the model.

| Device | Job | Actual session |
|---|---|---|
| Pacman | AntennaPod | ses_f738f52c7ffegRVJNkUGLkoCM0 |
| Pacman | Termux | ses_f738f0568ffebRX1XFFkOkiwgE |
| Lyriq1 | Tailscale Android | ses_f738ecfe6ffeXUxW3sPcUJ1eQR |
| Lyriq1 | Organic Maps | ses_f738e2e2bffeg3lpgLmEFLm062 |
| Lyriq2 | VLC Android | ses_f738df35dffers7C8LrjNYoVg4 |
| Lyriq2 | AppFlowy | Not submitted; starts after VLC is terminal |

All five submitted sessions were observed busy; no completion is yet counted.

## Initial observations, not final classifications

- AntennaPod inspected the existing checkout, clean status, revision and older
  artifacts rather than resetting the workspace. No historical artifact has
  been accepted as a new result.
- Termux investigated existing ARM AAPT2/AIDL inputs and build admission tools.
  It also attempted to read `/data/user/0/.../files/linux/backend.log` inside
  Fedora and suppressed the error. This is the same namespace confusion the
  harness must prevent; the private Android pathname does not become a guest
  pathname. Capture: pacman-ses_f738f0568ffebRX1XFFkOkiwgE-1789062673441.json.
- Empty `ps` results and missing `fuser` appeared in the initial checks. They
  must not be interpreted as proof that no sibling build exists. Watch the
  subsequent behavior before attributing a concurrency failure.

No build-command intervention has been made. Supervisor actions so far are
explicit prompt submission, read-only message/status/process capture and the
bounded Git metadata comparison described below.

First actual build commands are now running on Pacman: AntennaPod directly ran
clean :app:assembleFreeDebug with an ARM AAPT2 override; Termux invoked the
existing build-workload.py with --jobs 1. Neither has a terminal result yet.
AntennaPod selected --max-workers=2 despite the one-worker starting instruction;
record this compliance issue and actual resource impact, not an invented OOM.
Its Gradle version probe used a pipeline ending in tail before reading `$?`,
which reports tail's status. Its real build command does capture Gradle's exit
directly. These are distinct evidence scopes.

VLC and Organic Maps repeatedly searched / and unrelated directories before
creating their absent checkout. VLC then started cloning the supplied upstream
inside /workspace/tinyagent-six-builds/vlc-android. The fresh workspace differs
from Pacman's existing checkouts/tool caches; elapsed times are not comparable
as device-only performance numbers.

Harness version 13 now explicitly treats an absent checkout as normal, bounds
search to relevant workspaces before fetching the supplied source, distinguishes
Android diagnostic mappings from guest paths and warns against treating missing
process visibility as idle. Packaging verification passed. It is not installed
into the five running baseline sessions yet; its effectiveness is unproven.
Both Pacman build commands redirected output to files and only tail on exit,
leaving their active tool output empty. Version 13 also requires incremental
output or inspection of the same job/log, while retaining the actual command
exit code. This explains this observed quiet-tool case; it does not establish
the cause of every previously reported UI streaming bug.

## First Termux result and responsiveness observation

Termux's first Gradle invocation completed in 7m12s, exit 0, but packageDebug
and assembleDebug were UP-TO-DATE. The existing build verifier returned
status=failed and apks=[] rather than accepting historical artifacts. Its
recorded duration was 434.263s. The model inspected this contradictory-looking
result; recovery is still being observed. Do not count it as a new APK yet.
Evidence: evidence/campaign-termux-progress.json; build directory
/workspace/tinyagent-six-builds/termux-build-1789062728888602069.

Two WebView captures timed out and one direct /global/health request exceeded
30 seconds; a following direct session query succeeded. At the sampled point
Pacman had MemAvailable=5408648KiB, SwapFree=7682440KiB, app top-app cgroup,
OpenCode PID23218 alive and remaining Gradle processes alive. This establishes
transient API unresponsiveness under the campaign, not an OOM or its root cause.
No backend restart or duplicate build was used to recover observation.

Termux recognized the stale-artifact condition without supervisor intervention
and removed only its generated app/build directory before retrying. Signing
material and bootstrap archives were retained. The fresh retry is not yet
verified complete.

Root cause of one path-confusion prompt was in LocalLinuxRuntime's measured
text: it labeled an Android-private pathname simply "Runtime log". That line
now explicitly labels the Android-only mapping and points to app diagnostics.
This complements the fixed harness; it does not add sandbox access or expose
the log into Fedora. Device rollout/retest remain pending.

## Product follow-up prepared while jobs run

A supervisor read-only comparison requested the same public VLC info/refs URL
with curl, 30-second cap, discarding the body. Native Android curl under run-as
UID10151 returned HTTP200/55802bytes/9.474134s. Fedora curl through the actual
local backend returned HTTP200/55802bytes/8.029104s, exit0
(evidence/vlc-git-metadata-fedora.json, ses_f7378eba0ffex9W08hlOJM3zCW).
The Android run-as groups/SELinux domain and curl/TLS implementation differ
from the ordinary app process, so this is not a controlled PRoot-only timing
comparison. It establishes successful small metadata requests, not reliability
of large Git pack transfers or the cause of their EOF failures. No existing
clone, credentials, network settings or TLS verification were changed.

Organic Maps on Lyriq1 also failed its exact-revision depth-1 fetch with curl 56
TLS EOF (8612 bytes missing) after 6m25.543s. This is not a Lyriq2-only symptom.
The first command printed fetch_exit=0 because it read tail's pipeline status;
the model nevertheless recognized the actual Git error, then used pipefail and
PIPESTATUS in its retry. It changed repository-local HTTP version/buffer,
compression and negotiation settings together, so a successful retry would not
isolate which setting mattered. Certificate verification was not disabled.
The retry's Git/HTTPS processes were independently observed under app UID10042.
Capture: lyriq1-ses_f738e2e2bffeg3lpgLmEFLm062-1789063744031.json.

VLC's first clone ended with exit 128 (curl 56 unexpected TLS EOF, 5187 body
bytes missing, early EOF/invalid index-pack). The model checked the checkout
was absent before retrying with blob filtering and no checkout; it did not
replay an uncertain live clone. It also raised http.postBuffer for that command;
the captured error does not establish that setting as a necessary fix. No TLS
verification bypass was used. Evidence: evidence/campaign-vlc-progress.json.

DnfastRuntime now enables the existing DNFAST_REFRESH_TRACE output, which emits
origin/hash/stage information without URL credential/query payloads. PackageJobs
already captures these lines and terminal JSON is selected independently.
Build/lint passed; live APK rollout and observed intermediate progress remain
pending until active builds can be preserved. Do not count this as a verified
phone UX correction yet.

## First two completed campaign jobs: independent artifact checks

Pacman AntennaPod session ses_f738f52c7ffegRVJNkUGLkoCM0 is now idle after
clean assembleFreeDebug succeeded: log 21m10s, result wall time 1272s, 787 tasks.
Run antennapod-build-1789062742570993686 produced a new 26995013-byte APK,
SHA256 2eae0db96f7910954eb94934c709e36034b850e3c9cec5093ddfe8729ebcbcda.
The agent used two workers despite the prompt's one-worker start requirement.
It recovered from selecting x86-64 zipalign by choosing the installed ARM64
binary; signature/alignment checks then passed. Source revision stayed baseline.

Pacman Termux session ses_f738f0568ffebRX1XFFkOkiwgE is idle after its second
run termux-build-1789063343108186414 passed, 904.423s (Gradle 15m03s), five APKs.
Its first 434.263s attempt correctly failed artifact freshness validation.
The model recovered itself; no supervisor build or corrective prompt was sent.
ARM64 APK SHA256 ea8f8259ab523029f92bf12cf189f879c3b9070806d336dbf98dee42150b798e.
Its clean source revision and tool signature/alignment outputs are in the session.

Independent scripts/verify-campaign-apks.py checked both collected run logs,
copied all six APKs from the identified Pacman device, matched phone and host
SHA256 and recorded sizes, and checked every ZIP entry and AndroidManifest.xml.
Evidence: evidence/build-campaign/<run>/independent-apk-verification.json;
copies: artifacts/deepseek-campaign/<run>/. No app installation or launch was
performed. The verifier initially rejected AntennaPod's singular `apk` schema;
it now accepts that observed schema and Termux's `apks` list, and both passed.

Termux's final claim of no sibling Gradle/java processes is contradicted by
independent earlier process samples and the overlapping AntennaPod build.
Its 115628 KiB getrusage value is not total process-tree peak RSS. Do not use it
as peak build memory or compare phone performance with it. Harness v13 now
states the lock participation and child-RSS limits; rollout and model retest
remain pending. Both agents still tried an incompatible zipalign first despite
the existing ARM64 instruction, so an instruction alone is not yet proven enough.

Live remaining state at this capture: Tailscale is probing slow toolchain
downloads and redundantly searching for Go; Organic Maps is still busy; VLC
recovered its source fetch and is downloading Gradle. AppFlowy remains queued
behind VLC. Current campaign count is 2/6, excluding historical results.

## Pacman harness rollout and exact-model recheck

After both Pacman builds ended, server status was empty and native UID10223
contained only the app, PRoot and OpenCode. Updated in place to APK
2e10b7c0f22fb269197761cab15167b849a332b813b7dc50d3c8047d983584a3.
check-preview-update.py before/after preserved 100 listed sessions, backend
credential fingerprint, and connected provider IDs; all six campaign APKs were
copied and independently checked again after update. No reset/uninstall.

Restart refreshed the model catalog: deepseek-flash was absent while
deepseek-v4.1-flash was present. The diagnostic script now accepts the explicit
current 4.1 ID and checks model availability before creating a session. Empty
session ses_f736e5250ffe73lsfYxKCVZsHE received no prompt; no paid request was
replayed. Existing running campaign sessions and their historical model IDs
were not changed. AppFlowy's model ID needs fresh catalog validation at dispatch.

Actual opencode-go/deepseek-v4.1-flash retest ses_f736c97c5ffeeaW3ki2GuYk3wQ
finished idle without model error. It read harness13, correctly identified Stock
UID10223, did not seek ADB, and correctly rejected both the lock and RSS false
inferences. It located the ARM64 zipalign, but again inspected/attempted x86-64
tools and spent minutes finding binaries. The observation request timed out at
180s; the same session was recovered and completed, without duplicate execution.
Capture: pacman-ses_f736c97c5ffeeaW3ki2GuYk3wQ-1789065063352.json.

Root cause addressed next: configure-android-sdk-fedora.py emitted aapt2 but
omitted zipalign from android-build.json. It now verifies the adjacent zipalign's
AArch64 ELF header and records its path. Harness directs agents to this config
and warns that SDK version alone does not establish host architecture.
Supervisor staged the updated script on idle-build Pacman and ran it through
the actual Fedora backend: exit0, AIDL interface compile passed, both ARM tool
paths recorded (evidence/configure-sdk-h13.json). This is a supervisor environment
correction after the two completed jobs, not model-autonomous campaign work.
Latest local APK b3e7a4a5e87d7e00a2621d08e8a0e639aebb36b528e3eb33b761214975bfe1cb
passes assemble/lint/packaged-runtime checks but is not yet installed.

Organic Maps recovered a filtered depth1 fetch in 19.091s and started sparse
checkout. Its claim that the sibling saturates the network is unproven; observed
concurrent curl processes and ~31KB/s transfer do not establish that cause.

## ARM path retest and package output forwarding

Installed b3e7a4a5e87d7e00a2621d08e8a0e639aebb36b528e3eb33b761214975bfe1cb
on Pacman after idle API/process checks. campaign-arm-path-update-before/after
again verified sessions, provider IDs and backend credential preservation.
Fresh 4.1 session ses_f7367975bffePQyZAVKBR80gHd read android-build.json first,
selected its ARM64 zipalign without a filesystem search or x86 execution, and
verified the AntennaPod APK with exit0. Capture ends 1789065284023.json.
The model still wrote /tmp/za.log despite the diagnostic prompt saying no file
changes: alignment/path selection passed, strict read-only compliance did not.

Found a remaining progress forwarding gap: tinyagent-packages.py polled native
job output but printed nothing until completion. It now emits changed output
to stderr as it arrives, suppresses unchanged snapshots, identifies a rotated
log tail, and keeps stdout as one terminal JSON for existing consumers.
check-package-client.py reproduced the missing early progress before the fix;
afterward initial progress, repeated snapshots, appended output, log rotation,
terminal JSON, stable ID and no uncertain-submission replay checks all pass.
The staged client ran a real Pacman app-runtime check: job
375bec70-310c-45c3-af3c-f35041c13550, exit0, dnfast43b0928. Evidence:
package-progress-live-check.json. This short check proves integration, not
long-download intermediate timing; that live validation remains pending.
Latest local APK d5ef8aab9c96499d9de7f35a7d85aad31061e9b67235178027a59f2664f21d1d
passes build/lint/packaged-runtime checks; package-output change is not yet
installed as an APK. Pacman's installed APK remains b3e7a4a5.

Tailscale attempted a background download that did not survive its tool call,
then used curl --max-time110 with retries inside a 130s tool deadline. The tool
terminated that invocation; it inspected the original file/log/processes next.
This is an observed timeout-budget mismatch, not evidence that the download
needs another package manager or that the phone is intrinsically slower.

## Live package progress accepted on Pacman

Updated idle Pacman in place to d5ef8aab9c96499d9de7f35a7d85aad31061e9b67235178027a59f2664f21d1d.
campaign-package-progress-update-before/after verified the expected APK,
100 persisted session IDs, connected providers and backend credential fingerprint.
Refresh job 5adf71bb-f2d0-4bb8-8b07-078a3b7a7ace completed exit0 with HTTP and
planning trace forwarded into shell output; its first capture was already terminal.
To prove timing rather than infer it, check-package-progress-live.py observed a
second ordinary cache-preserving refresh while it ran, without restarting any
uncertain job. Job ff5fae61-e5df-4c08-8ca6-738ccbd71605, session
ses_f7362663effeSqUzyrxvsrdbp4, had 32 samples: a running tool exposed 706 bytes
of HTTP trace at 1789065538.858, before terminal exit0 at 1789065545.046.
Evidence: evidence/package-progress-live.json. The retained metadata generations
were reused; no cache deletion or cold-download claim. This proves the backend
tool-output path, not a rendered UI screenshot or a cold multi-minute transfer.
Verifier and artifact verifier added to private source export allowlist.

VLC's first Gradle download hit the 900000ms tool timeout with a 33533952-byte
partial ZIP. The model inspected the file then searched caches and tested other
URLs; the session remained busy. This is download preparation, not compile time.

## Bounded network comparison during outstanding downloads

Supervisor read-only range requests used the same public Google build-tools URL,
body discarded, max20s. No route/VPN/TLS trust setting changed and no archive
was supplied to the model. First range 0-1048575: Windows curl HTTP206/1048576B
in0.422965s; Lyriq2 native Android curl under app run-as HTTP206/1048576B in
15.937770s (65791B/s). Lyriq1 run-as was rejected with setegid permission error;
it produced no comparable measurement and was not retried with elevated UID.
Lyriq2 Fedora curl then received144479B/20.001096s, exit28 (7223B/s), evidence
lyriq2-fedora-range-compare.json. This single noisy difference is not PRoot proof.

Second comparison reversed order and used explicit HTTP/1.1, range0-262143:
Fedora HTTP206/262144B/3.355203s, exit0; native HTTP206/262144B/2.879280s.
Fedora DNS/connect/TLS/first-byte:1.162695/1.490532/1.889663/2.236642s;
native:0.813481/1.113102/1.435275/1.788302s. Evidence:
lyriq2-fedora-range-http11.json. Native and Fedora curl/TLS implementations and
run-as domain differ, phones have concurrent workloads, order/size also changed:
do not attribute improvement solely to HTTP version, claim an intrinsic 9x
PRoot slowdown, or globally force HTTP/1.1 from this evidence. Both completed
the second small request; large download reliability remains under observation.

## Model-owned segmented download recovery and notice inventory

VLC's model tested eight range requests and collected23895298 bytes, with one
part incomplete. Its ~955812B/s estimate divides by a nominal25s timeout rather
than measured wall time; do not treat the claimed47x ratio as a controlled
benchmark. It then wrote segdl.sh and started16-part Gradle acquisition with
expected SHA256 b266d5ff6b90eada6dc3b20cb090e3731302e553a27c5d3e4df1f0d76beaff06.
At capture1789065912213 the tool remained running, total137037885 bytes.
No supervisor download helper or bytes were supplied. Its helper's bare wait
does not reliably aggregate child failures and permits '-' to skip the hash;
the actual invocation provides a hash. Do not promote this helper into product
code or count the file complete before its integrity check succeeds.

During that live wait, release inventory checking was clarified: the original
RPM-only complete_notices=false is caused by libacl and zlib-ng-compat lacking
binary-RPM notice entries. The APK already includes three hash-verified notices
from their exact source RPMs. check-packaged-runtime.py now checks both inventories
and rejects packages without either matching route. All25 registered package
notice inventories are covered in the current APK. This is packaged-file coverage,
not a claim of a complete legal/license/source distribution audit. Original
collection metadata remains unchanged; no notice text or APK payload changed.

## VLC Gradle acquisition verified; current release variant built

VLC capture1789066024931 shows the model's segmented download assembled
137037885 bytes, passed SHA256 b266d5ff6b90eada6dc3b20cb090e3731302e553a27c5d3e4df1f0d76beaff06,
and exited0. The model proceeded to unzip/version/configuration; this is a
verified dependency download, not a completed VLC APK. Tailscale's resumable
Go download was actually progressing (~22KB/s in its captured curl log).

Host assembled and linted the current release variant with the existing private
release properties (no new key, no phone change, no publish). Current output:
app/build/outputs/apk/release/app-release.apk,
SHA256 c66b8b503f0201b0783921d3507aa63065e5718b9dbd753938275c3af34f2aa8.
Actual apksigner37.0.0 verification passed with certificate
c34483dc3b7228cede2e128ccd66cab193e78804686a58ea25ba318568afc9d2.
Manifest: io.github.gplaider.tinyagent, versionCode4/0.1.0-preview.5,
minSdk30/targetSdk36; badging did not report application-debuggable.
Release packaged-runtime checks passed including debug executable exclusions,
fixed harness, native/runtime pins, GUI and notice inventories. The initial
verification command used an absent36.0.0 SDK path; installed37.0.0 was then
located and used. This is a local candidate with the old preview version, not
a new publication or proof of production install/self-build acceptance.

## Production first install on idle Pacman started

Pacman had no production package. Native device serial and unlocked state were
rechecked; debug API reported no active sessions and UID10223 had no build child.
Installed the c66b8b50 release APK as io.github.gplaider.tinyagent successfully.
Stopped only the idle debug app to avoid its existing local backend port; kept
all debug data, provider credentials, sessions and workspaces. Production is a
separate package and does not imply automatic debug data migration.

Actual first-launch UI showed Stock/default app access and environment not ready.
Tapped environment preparation, then allowed Android notification permission
through the displayed system dialog. No self-ADB/Developer/Root setup was done.
Native process evidence: production UID10227, app27118 -> PRoot27210 -> tar27218.
Screenshot production-preparing.png shows extraction4021/5638 entries (71%) at
48s. After Home, production-background-notification.png shows ongoing preparation
and its cancel action in the notification shade. Returning to app at2m11s shows
package download/install preparation still active (production-after-prepare.png).
No Fedora ready/model-response claim yet. Debug app remains stopped with data
preserved while the separate production setup runs; other phones' builds stay
active. XML dump during the transition still contained the permission dialog,
so current visual state was checked with the screenshot instead of that stale
snapshot. Initial screen: production-first-launch.png/xml.

## New blocking package defect in the Tailscale campaign

Tailscale found missing zip/xz/bzip2/file/which/patch and used the documented
native package bridge. Job0624333a-45ca-4661-8dc3-00594a8c0021 failed exit1:
`transaction planning failed: planning root is unsafe: execution backend or app binding differs`.
Evidence: lyriq1-ses_f738ecfe6ffeXUxW3sPcUJ1eQR-1789066494281.json.
This invalidates treating prior deployment/check/hello success as proof that
new package installation continues working after every subsequent APK update.

Reactivated the owner-authorized dnfast correction thread
01a08be2-35c1-7b43-bd66-f2e9fb003393 with exact evidence and explicit no-phone-
mutation/no-binding-bypass/no-reset instructions. Requested actual field diff,
safe recovery contract and reproduced tests; parent retains phone rollout control.
Parent source inspection found DnfastRuntime hashes the guest argv before env,
including LocalLinuxRuntime's versioned sourceDir APK bind. Android replaces that
/data/app path on APK updates. This is a strong integration-side hypothesis,
not yet a measured persisted-versus-current binding field comparison. No root
journal or binding was altered and no security check was relaxed.

At this point production Pacman's separate first setup still has live UID10227
dnfast27379 under PRoot27371; no terminal preparation result yet. Its screenshot
at3m18s shows package download/install, not ready. Debug app remains stopped
with original data intact; the production test did not affect Lyriq1's binding.

## Production ready and stale planning lifecycle diagnosis

Production screenshot production-current.png now shows ready. Native production
UID10227 app27118 -> PRoot27711 -> OpenCode27719 was observed; setup completed
without app self-ADB/Root authorization. Tapping the actual chat button opened
an empty real session list (production-chat.png). No provider/model response has
been tested in this separate package yet. Its upstream channel indicator still
shows DEV despite a release APK; source titlebar ChannelIndicator keys this off
VITE_OPENCODE_CHANNEL, not Android privilege. This presentation issue is open.

Tailscale's install retried after recover and failed with the same binding error.
The dnfast investigation confirmed from source that planning snapshot equality,
not app runtime activation, rejects the stale binding. Recover retains old
reconciled history and does not publish a planning snapshot. repo refresh builds
a fresh snapshot when binding differs; migrate refuses Started/RpmResult work.
Therefore no weakened equality or rewritten journal is appropriate. TinyAgent
currently treats CLI/executor hash changes as updates but not all runtime/bind
changes. Parent owns the missing safe planning-refresh lifecycle fix; dnfast
thread is validating the proposed check/migrate/refresh and rejection contract.

A parent read-only cat of planning/current via package-bench-cdp timed out after
120s with no returned session ID. Do not repeat that request blindly; locate its
created 'Package benchmark: environment preflight' session before further reads.
No binding/state mutation was requested by that probe. The live old/current
field comparison is still unproven; diagnosis so far is code plus model failure.

## Agent recovery and host lifecycle correction

Capture lyriq1-ses_f738ecfe6ffeXUxW3sPcUJ1eQR-1789067270766.json proves the
Tailscale agent independently refreshed repositories (job
51864e45-7ee4-4175-973e-e6baa0183d0c), then installed the requested tools with
an applied transaction 8ee37d11-2524-7e7a-ac37-d65dc2a5cc72 and exit 0. Its
claim that a per-runtime memfd path caused the binding change is not proven.
The supervisor did not repair the phone's package state or supply downloaded
toolchain bytes. This is package recovery, not a completed Tailscale APK.

TinyAgent now checks a successful-planning binding marker before installation.
Changes run check, migrate, refresh, then a newly planned install, under the
same in-process writer. Native root locking, complete binding validation and
Started/RpmResult rejection remain authoritative. The marker includes the
root ID, backend/schema, actual UID/GID and launcher runtime/bind/CLI/executor
inputs; it is atomically saved only after a valid refresh terminal result and
an unchanged before/after fingerprint. It never authorizes transaction replay.

check-package-planning.py executes the production Java lifecycle methods with
a deterministic CLI double: unchanged fast path, changed-binding sequence,
check/migrate/refresh failures and invalid terminal results all pass. Android
Java compilation and lintDebug pass after correcting unavailable SDK methods
to readAllBytes and Os.getgid. This correction has not yet been installed or
verified across a real APK update; current phone campaigns remain uninterrupted.

Live captures also confirm Organic Maps (39 messages) and VLC (43 messages)
remain busy. VLC is fetching Maven AAR dependencies after Gradle acquisition;
this does not prove libVLC native compilation. AppFlowy remains unsubmitted.

## Pacman planning-update device verification

Candidate bbc2a1092288447dd180b600169b2ecb157f280568b282cd3c61e29a387a6f7b
passed assembleDebug, packaged runtime checks and a data-preserving Pacman
update. The production package was idle on an empty session list and was
stopped to avoid a second backend on port 4097; its data remains intact.
The debug package is now running. Both updates preserved the recorded 100
session IDs, connected provider IDs and private backend credential fingerprint
(planning-binding[-cached]-update-{before,after}.json).

First install request a29cbf2d-7e2c-43e9-9bc2-8781aced6ae2 automatically ran
check/migrate/refresh and a successful no-change hello install. Subsequent job
98f2d35e-6f70-4f30-a741-779dde7979c5 installed a new tree-2.2.1-4.fc44.aarch64
transaction without repeating refresh. /usr/bin/tree --version independently
returned tree v2.2.1, exit 0. Evidence: planning-binding-install.json,
planning-binding-new-package.json and planning-binding-tree-execution.json.

With the successful marker already saved, the same signed APK was installed
again using update installation. Job dc84f1af-de38-497e-8d99-46b44941fd5b
detected the changed execution inputs and again completed check/migrate/refresh
before a no-change tree request. This covers real cached-marker invalidation
on Android update, not just an absent marker. Evidence:
planning-binding-cached-update.json. Tests invoked the actual phone-local
backend shell/native package bridge; no model reasoning or production-package
provider execution is claimed by these checks.

## Harness 14: truthful versions and agent-owned Android execution

VLC capture lyriq2-ses_f738df35dffers7C8LrjNYoVg4-1789067848052.json shows
the agent linking ARM64 Build Tools 37 under a 36.0.0 directory and writing
Pkg.Revision=36.0.0 while linking the original package.xml. Executable startup
does not prove compatibility or truthful package identity. The active build is
still observed, not counted as a successful APK or native libVLC source build.

Harness 14 prohibits falsified toolchain metadata and requires explicit,
reviewable project version changes with build retests. ADB/ROOT instructions
also remove conflicting wording directing agent-requested installation back
to a user installer screen. The package lifecycle description now matches the
verified automatic safe replan behavior while preserving recovery boundaries.

Candidate b4fd3f0dad2b36f56051703cc9aadeafc83389d3e096f6e0c53fbbf6fbe2efa2
passed build/packaged payload checks and was installed on idle Pacman debug
without data reset. harness14-update-{before,after}.json confirms preservation.
DeepSeek 4.1 Flash session ses_f733cd046ffe8SreS0G7MGla9W read version 14,
rejected the hypothetical version spoof, supplied exact Developer shell/install
client commands despite empty Fedora adb devices, and distinguished hypothetical
Developer access from the actual measured Stock UID10223. Evidence:
harness14-model-check.json. This is model instruction compliance, not a new
successful physical Developer connection or installation proof.

Organic Maps ended its turn without an APK in capture
lyriq1-ses_f738e2e2bffeg3lpgLmEFLm062-1789067932108.json. Its ~9.3GB claim
conflates repository history size with pinned shallow working-tree bytes; its
sibling-contention causality is also not established. Supervisor sent one
follow-up to that same idle session to correct these inferences and reassess
bounded acquisition while preserving the partial clone and sibling work.
Receipt organic-source-followup.json records the exact intervention/model.
No duplicate session, checkout reset or external source transfer was performed.

## Production GUI channel indicator

The production GUI displayed DEV because ChannelIndicator used the upstream
channel name alone, despite Vite production mode. A one-line guard now hides
the dev-only indicator outside actual development mode; channel-dependent
workspace/tab behavior and beta labeling are unchanged. Pinned upstream GUI
production build passed with existing chunk/dynamic-import warnings, then all
952 staged GUI asset hashes and the APK runtime payload checks passed.

Candidate 4669e45b80aa3b0de1aab7fa99da12081e9dadba8b9f6fb89910a007b2ed25d9
is installed on idle Pacman debug with release-channel-update-{before,after}.json
preservation checks passing. Actual WebView screenshots
release-channel-webview.png and release-channel-session.png show no DEV badge.
The Playwright CDP check opened an existing model conversation and returned Home
without page errors or a Vite error overlay. The initial test selector confused
textContent with accessible name and timed out before clicking; using the
observed session text within the button fixed the test. No app restart was used
to repair a running UI; the app was started after the authorized APK update.
Browser-plugin skill unavailable; actual WebView CDP was used for this check.
The production-identity APK still needs rebuilding with these current assets.

## Current signed production candidate and UI provider test

Release build/lint and packaged runtime checks passed for APK
55cb0acf1a7229949f643b9e8349a846054be5cc5518e455c1262422d86fe434,
145208682 bytes. apksigner verified the existing production certificate
c34483dc3b7228cede2e128ccd66cab193e78804686a58ea25ba318568afc9d2.
The version remains preview.5; this is an unpublished candidate, not a new
GitHub release. It was update-installed on Pacman's production package.

After confirming debug sessions idle, the debug app was stopped to free port
4097. Production runs as UID10227: app29498 -> PRoot29574 -> OpenCode29580.
Its preserved Fedora environment opened an empty session list with no DEV badge.
Production WebView debugging was not enabled and no run-as access was used.
Through actual Android UI, Settings -> Providers -> OpenCode Go -> masked key
entry -> Continue completed using the owner's authorized test key (no key bytes
stored in these reports). The model picker exposed DeepSeek V4.1 Flash; it was
selected and one UI prompt requested uname, Fedora release, creation/readback of
/workspace/release-smoke.txt. The visible session title is
Fedora release smoke /workspace/release-smoke.txt. At this checkpoint it is
thinking, not a verified completed tool run. See release-ui-model-running.xml.

The production UI model run subsequently completed without restarting the app:
visible shell tools returned aarch64 and Fedora release 44, each exit 0, and
write/read tools produced release-smoke.txt. release-ui-model-complete.xml/png
capture the result and DeepSeek V4.1 Flash selection. Tapping the rendered file
path opened the native Open/Save/Share actions; Open independently displayed
the actual file contents `release smoke passed` (release-artifact-open.xml/png).
Thus evidence is not solely the model's narrative. UI elapsed label was 14s;
it is not an independently timed whole-onboarding duration.

After the completed run, production was force-stopped and launched again to
test recovery. The session list retained its entry; opening it restored the
response and selected DeepSeek model (release-ui-recovered.xml/png). The file
action again read the same actual workspace content after restart
(release-artifact-recovered.xml). One further UI read request was submitted
to test the saved provider connection; its completion is not yet claimed here.
The debug package remains stopped and all its benchmark data is preserved.

The follow-up after restart completed on the saved Go connection: one visible
read tool and exact response `release smoke passed`, DeepSeek V4.1 Flash, UI
elapsed label 8s. release-provider-followup.xml records the second response and
Send state (not Stop). Provider entry, model selection, response/tool execution,
artifact read and session/workspace/provider reuse are therefore exercised in
the signed production identity on Pacman. This does not extend verification to
other providers, Flip7, or all long-running/locked-screen scenarios.

## Long silent observation versus actual work

Tailscale capture lyriq1-ses_f738ecfe6ffeXUxW3sPcUJ1eQR-1789069414774.json
contains a running shell starting with `sleep 600` before checking Go module
download progress. Its start timestamp is 1789069000792. At epoch1789069501703
it had spent about501s in that observation command, not a single model response.
Native sampling in campaign-live-processes-1789069527.json independently found
UID10042 Go25291, Git29080/29083/29140, and separate sleep28077 still alive.
That sample found about4.0GB MemAvailable on Lyriq1 and4.6GB on Lyriq2; battery
temperature fields were250/260 (tenths of a degree). This is one operating
snapshot, not a controlled performance comparison. Lyriq2 then had only its
app/PRoot/OpenCode processes for UID10151, with no active Gradle process.

Harness15 now limits foreground observation waits to30s and distinguishes
observation waiting, model latency and real background progress. It preserves
the existing work/job identity and explicitly forbids cancellation or duplicate
submission just to return from a poll. This new instruction is not yet shipped
or model-retested; the signed55cb0acf candidate contains harness14.

VLC removed two RenderScript source-directory declarations after reporting
zero .rs files, so it is not yet evidence that a working feature was deliberately
removed. Its exact build retest remains authoritative; a source scan alone is
insufficient. The separately observed Build Tools version masquerade remains
a reported environment defect, irrespective of whether its next build passes.

Follow-up native ps returned no rows for the original observation shell28076
and sleep28077, so those handles have now exited. power diagnostics reported
mWakefulness=Dozing with TinyAgent:LocalRuntime PARTIAL_WAKE_LOCK held by
UID10042/PID5230 and isFrozen=false. See lyriq1-long-observation-power.json.
This supports runtime wake retention at that sample; it is not proof of every
background/network behavior or a total sleep duration measurement.

## Harness15 production update verification

Pacman's signed production APK is now 8c300eb85102d4e3f746ae0559d346754a62ea58761b6b9878ceaa9489bf1ebc
(145208910 bytes). The preserved production conversation completed its single
harness check on the saved OpenCode Go / DeepSeek V4.1 Flash connection.
The visible tools read the workspace file and installed AGENTS.md; the response
reported version15, maximum foreground polling wait30s, and inspecting the
original job instead of restarting a still-running background download.
Evidence: release-harness15-ui.xml, release-harness15.json. The UI returned to
Send state, without a duplicate prompt or restart. This verifies the installed
instruction and model interpretation, not yet long-running compliance.

New live captures confirm the old active campaign APKs remain running:
lyriq1-ses_f738ecfe6ffeXUxW3sPcUJ1eQR-1789070190457.json records68messages,
including a completed618.007s observation returning145MB/76module ZIPs and
another running sleep600. That observation delay also occurs on unit1; it is
not unique evidence of unit2 hardware slowness. No job was replayed.
lyriq2-ses_f738df35dffers7C8LrjNYoVg4-1789070175422.json records88messages
and the model's local mirror21364 performing a bounded56MB end-to-end fetch
test. Neither capture establishes a finished APK. AppFlowy remains unsubmitted.

Organic Maps capture lyriq1-ses_f738e2e2bffeg3lpgLmEFLm062-1789070284643.json
is busy with56messages. Lazy materialization failed with curl18/early EOF and
the android directory remained absent. Its `timeout ... git checkout ... | tail`
then `$?` reports the tail status, not a proven checkout success. The sparse
checkout failure also preceded its timing window. Therefore the printed
checkout_exit=0/elapsed=0s is not successful source acquisition evidence.
The harness already documents pipefail and immediate PIPESTATUS capture; this
case is a model-compliance defect to assess in its next recovery, not a reason
to count the transfer as passed or weaken the build gate.

## AppFlowy same-size corruption: reproduced and corrected

AppFlowy was submitted on Lyriq2 after the VLC session became idle, using
`opencode-go/deepseek-v4.1-flash`, session `ses_f725bf8a6ffe0unCSH3OWs0k4S`.
The agent's `af-raw-fetch.py` initially reused files and published downloads
based only on byte count. The supervisor captured that exact helper and ran
an offline counterexample: expected Git blob `good`, existing bytes `evil`,
both length 4. The helper returned success without checking the blob ID.
`evidence/reproduce-appflowy-size-only.py` failed with that observed behavior.

One recorded supervisor message requested Git blob OID validation on both
reuse and publication, preservation of live downloads and user edits, and
separate symlink handling. The agent rewrote its own helper. Independent
offline checks of the captured rewritten file passed corrupt-cache rejection,
corrupt-download rejection, valid-cache reuse and valid-download publication.
See `evidence/appflowy-blob-fix-check.json`. The existing phone session also
ran its self-test with valid-file, corruption and symlink cases, exit 0:
`evidence/go-campaign/lyriq2-appflowy-1789084905.json`.

The original transfer reported 4542 files in 682 seconds. That is not yet
full source-tree validation: the transfer ran before the validation fix.
The revised helper's scope/ownership and complete source tree still need
inspection before claiming safe general reuse or a completed AppFlowy APK.
This is an agent-created helper defect, not an established dnfast defect.

Follow-up phone verification of the selected `frontend/` subtree returned
`total=4542 missing=0 bad=0`, `verify_exit=0` at pinned commit
`5cf3a365dec0d59f64bad1ee4bb1050471a39b93`.
See `evidence/appflowy-frontend-blob-verification.json`. This covers that
subtree, not every repository path or an APK build. The agent then continued
toolchain inspection through the installed dnfast package client.

## AppFlowy dnfast planning failure: delegated for actual graph reproduction

The deployed revision `43b0928d6e8a3d76d6601f9c77e141970755b0a2`
failed before a transaction plan was published, with
`transaction planning failed: dependency graph contains a disconnected component`.
Both the original dependency list and a reduced eight-package list failed.
The latter job `8f37eca3-16b4-4ca0-845f-45cfbc130c97` returned exit 1;
the shell tool's enclosing echo can return 0, so that wrapper status is not
package-install success. Evidence: `evidence/dnfast-disconnected-component-failure.json`
and `evidence/go-campaign/lyriq2-appflowy-1789085594.json`.

The explicitly requested separate dnfast task is now confirmed active:
`01a08dc9-ae57-7cc2-9d46-92b0818717c1`, worktree `23f9`,
branch `codex/fix-native-dependency-reachability` based on the deployed revision.
It has acquired the phone's solver snapshot for host reproduction and is
investigating missing native dependency provenance. No fix or phone deployment
is claimed. The existing AppFlowy agent is testing a single `cmake` request;
any resulting phone state change must be accounted for before regression.

The single-package `cmake` attempt subsequently reached apply but failed with
`proposal is not a current canonical solver plan: canonical document failed: invalid plan: plan expired`,
job `449bf048-fbbd-493a-817a-9d39cd713b97`, exit 1. This is a distinct
observed failure, not proof of the disconnected graph's cause. The same
agent refreshed repository planning and retried; that retry was running
in `evidence/go-campaign/lyriq2-appflowy-1789085700.json`. Both failures
were delivered to the active dnfast fix task without disabling validation.

Lyriq1's Tailscale recovery now has actual execution evidence, not just a
promise to relaunch: launcher 27568, run `tailscale-run-1789085628`,
module download exit 0 and live gomobile test PID 27673 in
`evidence/go-campaign/lyriq1-usb-1789085687981.json`.
The agent captured the Gradle memory/worker changes before this rerun.
This is not yet an APK or proof that the effective JVM arguments match.

## Follow-up: dnfast1449710 phone update and exact request

The delegated task reproduced the graph failure with one fixed phone capture
and corrected missing RPM prerequisites and installed conditional dependency
provenance. It did not relax graph validation. The actual ARM64 runtime was
integrated and installed on Lyriq2 with OpenCode runtime6. Original root ID
and all 52 terminal journal files retained identical bytes. Existing provider
connectivity and both saved sessions were readable after the update.

The preserved AppFlowy session submitted the same eight-package request as
job `19d1060c-fcf4-40a8-8718-d22a7b2788e0`. The current inventory now includes
packages installed during intervening single-package attempts; this is not a
claim of a clean-root replay. New binding migration and repository planning
publication succeeded; the install process was still live at observation.
Final transaction success and APK output remain unverified.

## Follow-up: Tailscale prefetch and repeated TLS failures

The driver5 `make apk` returned exit 2 after another checksum-server TLS
handshake timeout, this time involving cloud.google.com/go/bigquery v1.3.0.
The earlier successful `go list -m all` did not prove that the subsequent
gomobile build could complete without further checksum requests. The agent
then ran `go mod graph` and `go list -deps`, both exit 0 on the first attempt.
This is successful prefetch evidence, not a successful Android build.

Read-only inspection of the actual driver and Makefile found no explicit
local GOMODCACHE override; Docker-specific cache overrides are a different
path. No cache-path mismatch is established. The prefetch command's target
environment still needs comparison with gomobile's Android invocation before
attributing the repeated failure to cache configuration or model reasoning.
TLS verification remained enabled. Logs are preserved in the existing session.

## Pacman VLC: final response while the native build remained active

The production UI returned to Send and showed a final response reporting the
native protobuf compilation as still running. The supervisor independently
queried PID 10442: it remained alive under production app UID 10227, elapsed
24:05. No successful APK or terminal build result was reported or verified.
This is an observation-continuity failure, not a false APK-success claim.
The supervisor resumed the same conversation once, explicitly retaining the
existing PID/log/exit marker and forbidding a duplicate build. Receipt:
`evidence/go-campaign/pacman-vlc-monitor-resume.json`. Model persistence after
that correction remains to be verified. Future-facing promises in a final
response do not constitute ongoing monitoring.

## Lyriq2: native network wait with continuing writes

The same dnfast PID 19061 showed syscall 207 in each sample, but process I/O
writes increased from 61,444,356 to 62,804,228 bytes over about 45 seconds.
The open artifact staging file and changing socket identity support ongoing
slow transfer, not a frozen process. This is not an exact network throughput
measurement. `evidence/sample-dnfast-progress.json` preserves all three samples.
The separate dnfast review passed 43 host timeout tests and did not establish
a product timeout defect; no speculative timeout patch was applied.

## Organic Maps: first Gradle build reached a terminal source/configuration error

Capture `evidence/go-campaign/lyriq1-usb-1789101750405.json` records `BUILD FAILED in 47m 30s`, at `:sdk:configureCMakeDebug[arm64-v8a]`. The reported errors are include failures in `3party/glaze/CMakeLists.txt` at lines3,11,12. Earlier CMake configuration output was progress, not a successful native build. The existing agent session continues investigating. Missing filenames and checkout integrity must be checked before assigning responsibility; the observed source include failures do not establish a dnfast package-manager defect.

The model's observation command buffered multiple minutes of sleep and filtered logs. The tool's generated description already discouraged output-truncating tail, but the pattern persisted despite harness20 on another device. This supports recording instruction noncompliance and improving visible execution state rather than assuming another prose reminder fixes it.

## Organic Maps: unsupported dependency pruning caused a second build failure

Capture `evidence/go-campaign/lyriq1-usb-1789105626197.json` records the next
native build failing after16m18s with `glm/geometric.hpp` missing. The model
explicitly acknowledged excluding glm and Vulkan-Headers as desktop-only.
Restoration output in `lyriq1-usb-1789106420254.json` reports pinned glm1673 files
and Vulkan-Headers49 files fetched, exit0, followed by the same Gradle task.
That output is the helper's reported result, not independent whole-checkout
verification. No successful Organic APK is established yet.

Prevention target: derive dependency pruning from the actual Android build
graph, not library names or assumed platform roles. Inspect required includes
and pinned submodule contents before another expensive compile. Preserve
partial object outputs and failure logs. This is a source-preparation/model
mistake; these observations do not establish a dnfast defect.

## AppFlowy and observation transport

`evidence/go-campaign/lyriq2-appflowy-usb-1789106414.json` shows Cargo's cache
growing633 to635 files with PID2441 still reported alive and HTTP/2
INTERNAL_ERROR retries. This supports slow progress, not completed provisioning
or an APK. The earlier diagnostic failed because it targeted an unavailable
Tailscale endpoint; a USB reader verified serialZY22HZPLL8 via MacBook and read
the existing backend without restarting it. No credentials were printed.
At the same check Windows ADB listed no devices, so Pacman's current native
build state is unknown, not terminal. Do not restart merely to restore visibility.

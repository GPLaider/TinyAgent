# Current-source self-build on Lyriq1 — first run failed, correction under validation

Source: private repository commit `a203aa78886561870bdc4555a70cacf8540e6ad8`.
Bundle SHA-256: `570854c82ec5f1314c8d569674f051bf795a7299185510f7d51b584d01a474c7`.
Phone workspace: `/workspace/tinyagent-selfbuild-a203aa7`.
Model session: `ses_f756260ffffey0f8IzaNJ7G18o`, OpenAI gpt-5.6-luna,
using the existing OAuth and a dedicated QA session.

Read-only preflight confirmed Fedora 44 ARM64, Java 17.0.20.1 and working ARM
aapt2, but no TinyAgent checkout or development signing identity. Existing
signer was provisioned to app-private storage with file mode 600. Only the host
ADB daemon was temporarily switched to root because this ROM's shell run-as
failed setegid; it was restored to shell UID2000 immediately after provisioning.
No TinyAgent Developer pairing or Root selection was made. The model's live
Android bridge measured selected_transport=stock, root_selected=false and
execution_uid=10042 after restoration.

The source-only server bound host loopback and exposed one exact Git bundle,
not a directory. After the model downloaded and verified it, the server closed
and its device reverse mapping was removed. No signing material was sent
through that server. Clone and exact checkout succeeded. The shared signer
certificate is the existing development anchor
`a3ef78ae0bfdfc30307e3448e138eca29adf39d966f89af116bbce151abc1ed2`.

Actual command: `/usr/bin/bash scripts/self-build-complete-fedora.sh`,
workdir above, requested tool timeout 1800000 ms. Observed app UID10042 chain:
app925 → PRoot6614 → OpenCode6621 → bash7110 → bash7114 → bash7117 → microdnf7122.
Output includes environment=fedora-local, the exact source directory and
fedora_https=200. The first build exited 1 during runtime asset staging; no APK was produced.
Transcript: `evidence/ses_f756260ffffey0f8IzaNJ7G18o-probe.json`.

Observe the same session/process before any retry. Tool observation expiration
does not authorize another build. The first run is collecting failure evidence
without model source edits. This is a development-signed self-build attempt;
production-key phone build/update remains separate and unverified.

## Runtime staging failure and corrected input path

The a203aa7 self-build script packages the patched runtime into the same
`artifacts/opencode-linux-arm64.tar.gz` path used by the official upstream
collector. The collector verifies an existing file against the upstream digest,
so a subsequent run would reject that overwritten cache. The current first
phone run was not changed in flight.

The phone packaged a verified backend binary into a different gzip byte stream:
`8140128407d95db31b782056b07ea42fc363e953827cda8937bfee5b3b5a5669`,
49,630,217 bytes. The required archive is
`5139469d4fa9b7371129a956765d7ede425232c4d6bdbb07ab86f966c56fe2a2`.
The binary check passed but archive staging correctly rejected it. Host/phone
compression differences are suspected; the exact compressor cause was not measured.

The corrected self-build uses `--installed-apk "$TINYAGENT_APK"` to copy exact
shipped runtime archives. LocalLinuxRuntime binds its own installed sourceDir
at `/tinyagent-installed.apk` and sets TINYAGENT_APK. Android prevents the app
UID from writing its installed APK. The archive hashes remain pinned. This
build compiles the GUI and APK; its backend remains a prebuilt dependency.

Host check-runtime-input-separation.py passes cache preservation, exact APK
asset reuse and rejection of changed runtime bytes. Staging from the actual
TinyAgent-gui-prod-channel.apk also passes both fixed hashes. The new native
binding and a complete corrected phone build still require device validation.
Retain the first failed checkout and its changed runtime manifest as evidence.

## Installed input binding verified on Lyriq1

Candidate APK SHA-256:
`6dd6715457d7ec2355e0656a206f6bf1ffafd73dc4512bc14670476aa4885d73`.
Clean assembleDebug/lintDebug, packaged runtime/harness/GUI checks and the
existing development signer verification passed. Exact-hash reconstruction and
`pm install -r` succeeded. All 45 existing session IDs, openai/opencode provider
connections and dark theme remained after the update.

Actual Luna session `ses_f755055eeffeuuWEVjMB3FOHmi` read the updated harness,
hashed both embedded runtime archives successfully (Fedora 52,186,116 bytes;
OpenCode 49,796,227 bytes), and received PermissionError when opening the APK
O_WRONLY without truncation or any write. Live Android diagnostics measured
execution_uid=10042, selected_transport=stock and root_selected=false.
Transcript: `evidence/ses_f755055eeffeuuWEVjMB3FOHmi-probe.json`.
This proves the corrected runtime input path, not completion of the next full
self-build or production-signing acceptance.

# dnfast product integration candidate

Phone workloads were paused until full dnfast deployment. All three phones have
now passed the actual product package path at revision 43b0928: runtime check,
repository refresh, hello/info installation and hello execution. The authorized
DeepSeek 4.1 Flash campaign is now being submitted; submission is not build
completion. Per-job receipts are under evidence/go-campaign/*-run.json.

Lyriq2's successful refresh job is 90e93028-fe87-43bb-8263-60bedfab9bba
(about 19m40s), followed by install job 1ba6c47b-b9d3-4f60-84be-4af8f6e3d7d0,
transaction 2817e35c-9504-7757-8689-bddc7a64f10e. Both exited zero and
/usr/bin/hello printed Hello, world! with zero exit. Evidence:
dnfast-lyriq2-refresh-status.json, dnfast-lyriq2-install-after-refresh.json,
dnfast-lyriq2-hello-after-install.json in evidence/. The earlier missing-planning
failure followed an incorrectly submitted refresh command; the correct refresh
resolved it. Do not claim this proves every initialization/recovery path.

The long refresh prompted timeout investigation in the existing dnfast thread.
Important correction: fixed /proc/io counters and repeated recvfrom snapshots
do not prove continuous socket inactivity; socket reads are not fully counted
by those VFS counters. Independent ARM64 native/PRoot TLS tests passed. No
network-timeout defect is yet confirmed; retain the observation limits.

Lyriq 1 (`ZY22J58799`) also installed APK
`a3689c9865a6029cad55c5ea5241000eb42b4f1165c542bec477e8227a2f1927`;
the installed file hash was read back. Its actual WebView/backend package bridge
passed check, refresh, installation of hello/info, and hello execution.
Install job `ad045b98-bc5d-4c5f-901b-33e47dc5e0ac` applied transaction
`1017103f-7762-7769-8bb9-bc267dabec5e`. Check/refresh evidence includes
`package-bench-lyriq1-probe-1789056541974.json` and
`package-bench-lyriq1-probe-1789056651250.json`; subsequent timestamped records
retain install/hello results. Go key save returned success and the connected
provider list retained `openai`. This does not prove OAuth refresh or successful
DeepSeek inference. App stopped after validation.

Lyriq 2 installed the same candidate after a 17-second peer transfer from unit 1;
the installed APK hash was read back and matched. Its app-runtime check passed
(job `c49a3f7e-e074-4138-849e-5727327a1710`). The supervisor then incorrectly
invoked client `refresh` instead of `repo refresh`; that command was rejected
with exit 2 and was not a successful refresh. Subsequent hello installation
failed with exit 1: `open directory parent_fd=9 child="planning": No such file
or directory`. Job: `9e2d4f3a-497c-45fa-8912-9e240859b98e`, evidence:
`dnfast-lyriq2-43b0928-product-install.json`. No package was reported applied.
Deployment on unit 2 is NOT validated. The app was stopped after the terminal
failure when the owner requested a work/instruction accounting. No six-app
campaign has been submitted. Correct refresh and root-state diagnosis remain
pending; do not infer the cause from this message alone.

## Inputs and execution

- Source revision: `43b0928d6e8a3d76d6601f9c77e141970755b0a2`.
- Pinned manifest: `runtime/dnfast-43b0928-manifest.json`.
- Overlay SHA-256: `c1f310670f0c84675ed9dfcb45c05beac8ffad32c2856ac96bbd66d720cdd7cd`.
- 33 regular files, including the CLI, executor and private shared libraries.
- `runtime/dnfast-library-provenance.json` maps all 31 library hashes to 25 exact
  RPM package versions from the original 16c6887 ARM build manifest. The new
  candidate reuses those exact library bytes under a new private prefix and
  rebuilds both executables. The current manifest records their source/final
  hashes. Attribution does not establish fresh RPM signature verification.
- Android app UID launches `libdnfastlaunch.so` before PRoot for each request.
  The launcher supplies the sealed context and root lock. The existing OpenCode
  shell cannot substitute for that launch contract.
- Initial package provisioning uses `LocalLinuxRuntime.runPackages`. Subsequent
  Fedora requests use `bootstrap/tinyagent-packages.py` and the same-UID Unix
  socket bridge. No ADB is required for these package operations.
- Package jobs persist IDs and output under app files `linux/package-jobs`.
  Client disconnection does not cancel the transaction. Query the printed UUID
  before retrying; cancellation is a separate request.

## Host checks completed

- `check-package-jobs-cancel.py .checks/json-20240303.jar`: real PackageJobs source
  with deterministic platform/runtime doubles; cancellation survives late output
  and a successful exit racing with cancellation. This does not test Android
  process termination or AtomicFile crash durability.
- `check-package-client.py`: one submission, stable UUID, polling, no automatic
  retry after an uncertain response. This uses a fake transport.
- `check-dnfast-self-build-inputs.py`: reuses the actual candidate APK's exact
  dnfast bytes in a temporary source tree. Corrupt manifest and overlay are
  rejected without replacing previously verified files.
- `assembleDebug` and `check-packaged-runtime.py` passed for the candidate with
  seven bootstrap scripts and harness v11.
- `check-dnfast-empty-upgrade.py` on Linux: root lock contention, existing state,
  unknown binaries and symlinks refuse changes; interrupted publication resumes
  while preserving root ID and both original binaries. Synthetic byte fixtures
  test updater logic, separate from the real Pacman evidence below.

`self-build-complete-fedora.sh` now stages dnfast from `TINYAGENT_APK` using
`stage-dnfast-runtime.py --installed-apk`. It does not recompress or weaken pins.
Older APKs without the dnfast assets fail rather than silently creating an
incomplete self-build.

## Still required

Pinned dnfast source has been exported with `collect-dnfast-sources.py CHECKOUT`
to `artifacts/native-sources/dnfast-43b0928d6e8a3d76d6601f9c77e141970755b0a2.tar`.
`runtime/dnfast-source-export.json` records its digest and the exact LICENSE
digest checked in APK assets. Export disables Windows line-ending conversion.
This archive is a fresh Git source export, not the original build source bundle
identified by the overlay manifest; their different hashes are not interchangeable.

- Pacman's original memfd failure is fixed. The product root was upgraded with
  its original binaries backed up. Real OpenCode shell/package-client/native-job
  check, refresh, hello/info install and hello execution passed with exit 0.
  See `DNFAST-PACMAN-MEMFD.md` for APK hash, IDs and evidence. This does not prove
  populated-journal migration, package cancellation or all-device deployment.
- Complete source and license records for the overlay dependencies and Rust crates.
  The pinned dnfast Cargo.toml declares `GPL-2.0-or-later`; its LICENSE contains
  GPL version 2. This observation is not a complete dependency/license inventory.
- Validate native launcher rebuilding in ARM Fedora, then build and sign the full
  TinyAgent APK there and verify update identity and retained data.
- Verify all product package-management paths, progress reporting and recovery UX
  before calling the deployment complete or resuming the six-app campaign.
- No dnfast-versus-microdnf performance conclusion has been measured here.

The original build image now supplies 47 verified license files. Where a
subpackage declares none, the collector attributes notices only from installed
packages with the exact same source RPM. `libacl` and `zlib-ng-compat` have no
notice in that image collection. Three supplemental notices were extracted
from their exact source RPM versions downloaded from Fedora Koji; source RPM
hashes and archive members are recorded separately in
`runtime/dnfast-additional-source-rpms.json` and `runtime/dnfast-source-notices.json`.
Those downloads have not undergone RPM signature verification. The original
image report remains unchanged in scope. The source RPM collection below is now
complete. Rust notices have been checked against the captured ARM64 dependency
graph; final release packaging of those notices remains open.

`scripts/collect-dnfast-library-sources.py` collects the exact 24 unique source
RPMs corresponding to those 25 binary packages. Its receipt is
`runtime/dnfast-library-sources.json`; all 24 downloaded and a second pass
verified every cached URL/hash. These HTTPS/hash records do not establish RPM
signature trust.

All 241 registry packages in the exact Cargo.lock are now exported, including
dev and other-target packages. Cached or downloaded `.crate` archives were
checked against each locked checksum; missing count is zero. Local archive
`artifacts/native-sources/dnfast-cargo-sources.tar` has SHA256
`f88418a8272097b3bbbb68adf182286a1b7afe5fc02d97388d70d44b8cdc077a`, verified
after transfer. `runtime/dnfast-cargo-sources.json` records every version/hash.
This source collection does not claim all 241 packages are linked into the APK
or that the compiled dependency notice inventory is complete.

The source archives supplied 452 notice files, stored in
`artifacts/native-sources/dnfast-cargo-notices.tar` (SHA256
`244fbd492ce3421a9cc32b082d2d226dc09ebad973afedfea127da26d7753d5b`).
Four locked crates have no notice files, but none occur in the captured
`aarch64-unknown-linux-gnu` normal/build graph for dnfast-cli and dnfast-executor.
That graph was queried offline in the original build image, with the original
source/cache mounted read-only. All 173 external packages in the graph have
retained notices. `scripts/check-dnfast-target-notices.py` verifies the graph
against the notice inventory; its report and invocation are in `runtime/`.
This is default-feature target dependency coverage, not ELF symbol attribution.
The notice archive is now included as assets/licenses/dnfast-cargo-notices.tar
in the locally rebuilt debug APK. check-packaged-runtime.py verifies its exact
SHA256 against runtime/dnfast-cargo-notices.json, and the private source export
includes the archive. Installed phone candidates have not been updated solely
for this packaging change; final release signing/distribution remains pending.

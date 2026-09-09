# Capability and development bootstrap integration

## Verified v8

APK SHA256: `3e234a6681df985e87dd40652e498c03bae2e3c792501571279748b3aad900cb`.
All installation routes used that same APK: Stock PackageInstaller and Developer
UID 2000 on Pacman 000501423003390, Root UID 0 on Edge ZY22HZPLL8. Each passed
three consecutive fixture installs. Reports: `evidence/install-*.json`.

Actual Fedora calls reached the Android diagnostic bridge on both phones.
Kernel peer UID checks rejected host ADB callers; root availability did not
silently satisfy the Developer route. Root inspection passed three times on
Edge. Reports: `evidence/android-bridge-integration-*.json`.

Edge Fedora processed Android inspection JSON into `/shared`, and Android read
back the identical SHA256. Reports: `evidence/android-fedora-exchange*.json`.
These are real tool executions without model inference.

An update regression was reproduced: older prepared installations lacked the
`wanted` preference and did not resume. Migration now resumes only an actually
prepared legacy Ready runtime; explicit Stop stays stopped. Before/after logs
are `evidence/edge40-legacy-resume-*.log`. The saved phone-build session remained
readable. Pacman passed three stop/start cycles plus force-stop/reopen.
LocalPolicyCheck has 99 passing assertions.

## v9 bootstrap

Four versioned development preparation scripts are generated into the APK by
Gradle Sync and copied to `/root/.tinyagent/bootstrap`. Harness v4 supplies the
exact command. OpenCode's existing bash execution provides output and process
control; no second job scheduler was added.

SDK preparation serializes concurrent runs, downloads into `.part`, verifies
size/hash before publication, and extracts into a temporary directory before
rename. `prepare-android-sdk-fedora.py --self-check` passed interrupted-download
retry, rejected traversal and atomic extraction checks. Existing legacy partial
extraction directories are not automatically repaired.

The ARM64 SDK layout now includes verified platform-tools. The full self-build
runner prepares tools and source license notices before building. Host v9 build,
lint and all packaged script/runtime/native/GUI hash checks passed.

v9 APK SHA256: `a1dd143f898b76f1ab9bee708236d822cd4c608986e07efbfd1a1b8a5d4616e0`.
It updated Edge successfully with the existing host debug signer. The packaged
bootstrap ran through the actual phone-local OpenCode shell and returned
`sdk_inputs_exit=0`, `sdk_config_exit=0`, `development_prepare_exit=0`.
This reused already installed packages/verified SDK inputs, not a clean download.
Report: `evidence/edge40-packaged-development-bootstrap.json`.

Neither device is an unchanged stock phone. OAuth/model inference, privileged
ROM installation success, clean stock installation, 16 KiB support and formal
release signing remain unverified. The phone-built debug signer differs from
the installed host debug signer; no key was copied and no signature check was
bypassed.

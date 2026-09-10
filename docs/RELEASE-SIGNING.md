# Production signing and candidate status

Production package: `io.github.gplaider.tinyagent`.
Development package remains `io.github.gplaider.tinyagent.debug` with its existing
signer and data. Changing from that package is not an in-place update or an
automatic OAuth/session migration.

Production certificate SHA-256:
`c34483dc3b7228cede2e128ccd66cab193e78804686a58ea25ba318568afc9d2`.
RSA 4096, alias `tinyagent-release`. Created on 2026-09-10.
The key and properties are in `D:/TinyAgent-work/private-signing`, outside the
source repositories, with inheritance disabled and access granted to the
current Windows account. No key or password is included in the source export.
Back up this identity securely; a replacement key cannot update installed APKs.
No backup or phone provisioning of this production key has yet been performed.

`scripts/prepare-release-signing.py <new-private-directory>` provisions a new
identity only for a genuinely new distribution. It refuses an existing
directory and any directory inside a Git repository. Do not run it to rebuild
an existing release. Reuse the original key and properties instead.

After staging the pinned runtime, native and GUI inputs, build on this host:

```powershell
$env:GRADLE_USER_HOME='D:/TinyAgent-work/gradle-home'
$env:ANDROID_HOME='C:/Users/Administrator/AppData/Local/Android/Sdk'
$env:JAVA_TOOL_OPTIONS='-Djava.io.tmpdir=D:/TinyAgent-work/jtmp -Djdk.net.unixdomain.tmpdir=D:/TinyAgent-work/jtmp'
$env:TINYAGENT_RELEASE_SIGNING_PROPERTIES='D:/TinyAgent-work/private-signing/release.properties'
./gradlew.bat :app:clean :app:assembleRelease :app:lintRelease --offline --no-daemon
python scripts/check-packaged-runtime.py --variant release --apk app/build/outputs/apk/release/app-release.apk
```

Always run Android SDK apksigner verify --print-certs and compare the certificate
to the fingerprint above before distribution. A Gradle assembleRelease without
configured signing can produce an unsigned artifact; build success alone does
not satisfy this gate. Confirm package, version, min/target SDK and absence of
debuggable/debug probe activities from the actual manifest.

Phone self-build supports `TINYAGENT_BUILD_TYPE=release` and requires
`TINYAGENT_RELEASE_SIGNING_PROPERTIES` pointing to the same identity, with paths
adapted to the phone. Missing signing input fails before Gradle execution.
Default self-build remains debug and requires its existing shared development
key. Production phone signing/build/update remains unverified.
The real build wrapper passed a host test with fake compiler tools for debug
default, missing production signer rejection before Gradle, release task
selection, and invalid variant rejection. Run
`python scripts/check-phone-build-variant.py`. This checks dispatch and guards,
not compilation or certificate validity; the actual host release build below
provides separate signing evidence.

## First signed candidate

Artifact: `TinyAgent-0.1.0-preview.4-production-signed.apk`
SHA-256: `807e820496bf53717ff7c4d7a79869f64b262364e2e137791410a4e3ae3003d8`
Size: 126705647 bytes. Version code 3 / 0.1.0-preview.4.
Android API 30 minimum, target 36, ARM64.

Clean assembleRelease + lintRelease passed (55 tasks). Packaged fixed harness,
bootstrap scripts, PRoot tracer/loader and dependencies, notices, runtime
archives and 952 GUI asset hashes passed. Debug native probes were absent.
apksigner verified the production certificate above. Actual manifest inspection
found no debuggable flag or debug probe activities.

This candidate was installed on Lyriq1 ZY22J58799 as a separate package; initial
Stock preparation completed under app UID10000 in approximately 12 minutes,
including 158 package downloads and the installation transaction. The existing development
app was not deleted or cleared; its idle backend was stopped to avoid port
4097 conflict. Before this test, 43 development sessions, connected providers
and dark theme were recorded in `production-coexist-before.json`.
The actual UI reached the fresh session list. A new session using default
Big Pickle completed pwd, uname -m and cat /etc/fedora-release after one-time
approval of /etc access. Expanded shell output showed Fedora release 44,
and the final answer showed /workspace and aarch64. This was native touch/text
input and rendered-result inspection, not a host API substitute. The new
package did not import OAuth from the development app.

Evidence: `evidence/lyriq1-v4-release-ui-setup.json` (exact installed hash,
app UID and PRoot/OpenCode process chain), `lyriq1-production-first-chat.png`,
`lyriq1-production-first-response.png`, and
`production-coexist-before.json` / `production-coexist-after.json`.
Afterward the production backend was stopped and the development backend
restored. All 43 prior development session IDs, providers and dark theme
were retained; only UID10042 had running PRoot/OpenCode afterward.

The candidate has not been published. This is one first-install and
model/tool journey, not three consecutive passes. Production OAuth/provider
matrix, recovery, phone self-build and same-signer update validation remain.
Existing development-package passes do not satisfy these gates. The
distribution repository remains private.

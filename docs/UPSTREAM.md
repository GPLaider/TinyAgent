# Pinned upstreams and preparation

OpenCode release: `v1.18.29`
Source commit: `16747470f976aca3d362ad730bcd3fe82ecc2c9a`
Official repository: https://github.com/anomalyco/opencode
License: MIT; retain the complete copyright and permission notice in the APK,
source distribution and runtime distribution.
Required source build package manager: `bun@1.3.14`.

TinyAgent is an independent project. It is not an official OpenCode Android app.

## Source and GUI reuse

The existing desktop-style and mobile UI, session store, provider/auth settings,
model selection, streamed output, tool permissions and code/diff rendering are
provided by the upstream source. Do not build a parallel model/provider client
in the Android wrapper. The intended backend is the pinned v1 server because
the pinned GUI's custom-provider save flow explicitly requires v1.

The source build embeds the web app by default. The Android wrapper must connect
to the phone's loopback backend. A host-side server is a development aid and
cannot satisfy the phone-only acceptance requirement.

Persist data/config/state and workspaces independently from the versioned runtime.
Do not leave `OPENCODE_AUTH_CONTENT` set after onboarding: in this version it can
override subsequently saved authentication files. Test key rotation, endpoint
changes and reauthentication against the backend, not just form persistence.

## Verified-download procedure

From the TinyAgent project root:

```text
python scripts/collect_upstream.py --self-check
python scripts/collect_upstream.py
```

The collector requires network access and native `gpgv`. It downloads public
Fedora signing keys into its own artifact directory, verifies the pinned Fedora
44 primary fingerprint, then checks the signed archive SHA256. It also verifies
OpenCode Linux ARM64 bytes against the official GitHub release API digest and
size. The latter is HTTPS/API digest verification, not release attestation.

Fedora source:
`Fedora-Container-Base-Generic-Minimal-44-1.7.aarch64.oci.tar.xz`

Expected SHA256:
`2c00fc0e7890a5bfecbd243561e5a2d07d2661667e1b897eab549b83f6b1db9a`

Fedora 44 key fingerprint:
`36F612DCF27F7D1A48A835E4DBFCF71C6D9F90A6`

Sources: https://www.fedoraproject.org/misc/ and
https://www.fedoraproject.org/security/ . Archive/signature verification succeeded
again inside the app-owned Edge 40 Fedora on 2026-09-08; the successful collector
output precedes the later GUI failure in `evidence/edge40-stock-self-build.json`.

The archive is an OCI image layout, not a ready-to-extract rootfs tar. Provisioning
must verify every selected descriptor/digest and apply ordered layers, whiteouts,
ownership, modes and links safely. The current collector deliberately performs
no extraction, phone installation or runtime activation.

## Distribution work still required

- Integrate the actual PreRoot source/entrypoint and verify its license.
- Prepare and test Fedora packages, DNS/network handling, Git, compiler and tests.
- Keep prior runtime available while staging an update; switch only after health
  checks and preserve all user data. No updater is implemented yet.
- Include Bun/JavaScriptCore/WebKit and bundled-library notices, corresponding
  sources and any required relinking/rebuild instructions. OpenCode's MIT file
  alone is insufficient. Reference: https://bun.sh/docs/project/license .
- Generate the final dependency inventory from the exact shipped APK/runtime.
- Generate a dedicated release signer, preserve it securely, record its public
  certificate digest and verify each candidate with `apksigner` before installation.

## Evidence gate

`python scripts/check-release.py --self-check` tests the gate using synthetic data.
It does not install an APK or count as a device test.

`python scripts/check-release.py evidence/candidate.json` checks that a real
candidate dossier contains matching artifact/log hashes and three consecutive
complete rounds on the same device and APK. It checks evidence completeness;
it cannot establish that a human-written success statement is truthful. Collect
and inspect actual UI, process, file-diff and exit-status evidence first.

No passing candidate dossier is present at this stage.

## Native source/notice collection, 2026-09-08

`scripts/collect-proot-sources.py` verified source archives for PRoot 5.1.107.92,
talloc 2.4.3 and libandroid-shmem 0.7 against the official Termux recipe hashes.
It also retained Termux build recipes at revision
`ff422d48d23ad12e8ffba021c2fa3a5c6b4f138e`. The records and exact archive hashes
are in `evidence/native-source-collection.json`; archives are in the ignored
`artifacts/native-sources` directory and can be collected again by the script.

Three original source license files and the GPLv3 text are included as APK
assets. talloc's source COPYING contains LGPLv3, while Termux's package metadata
labels it GPL-3.0; this distinction is retained in THIRD-PARTY-NOTICES.txt.
This collection does not prove the complete dependency/source closure or
reproduction of the shipped Termux binaries. Those remain release gates.

Host-built capabilities-v5 SHA256:
`9c4641b653a0549c9cea32567f910003b95385fe1450a7856caa06ff8764612e`.
assembleDebug and lintDebug passed. `check-packaged-runtime.py` verified all four
native notice hashes inside the APK, in addition to the native, GUI and runtime
hashes. v5 is debug-signed and has not been installed for device acceptance.

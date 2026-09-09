# Setup integration checkpoint

Historical restricted-access checkpoint. The patch has since been applied to
the canonical project and further fixed on device. Do not reapply it there.
See `STATUS.md` for current APK, device results and remaining work.

This staged source is under the writable current workspace in `TinyAgent-next`.
The canonical `D:/TinyAgent-work/tinyagent` was read but not modified this turn.
The current managed environment does not grant writes to that canonical path.

## Implemented in staged source

- APK assets include the pinned Fedora layer and OpenCode ARM64 archive.
  `scripts/stage-runtime-assets.py ARTIFACT_DIRECTORY` reproduces this staging.
  These are public verified archives, not device credentials. Archives remain
  outside source control and add about 113 MB to the APK before packaging.
- The native setup button starts a non-exported foreground dataSync service.
  It re-verifies the app-private self-ADB nonce and root permission before
  giving a fixed installation script the packaged archive paths.
- PreRoot copies inputs into root-owned staging before hash verification and
  extraction. A completed version is reused and subsequently version-probed;
  incomplete staging is retained and refused rather than overwritten.
- Production execution binds persistent backend home, workspace storage and
  shared files outside the versioned Fedora root. The existing diagnostic
  root path and its live backend are unchanged.
- Setup progress survives Activity recreation in preferences. The service is
  not automatically restarted; interrupted writes must be reconciled first.
- SelfAdbClient now closes a candidate that races with connection cancellation,
  and requires nonce verification before installation writes.

## Verification and limits

Host archive SHA256 checks (2), shell syntax and mocked-identity installation
precondition checks (4) passed. Existing pure Java policy checks passed (58).
The identity mocks do not represent actual Android behavior.

The Android Java compiler reached class generation without source diagnostics,
then failed closing its JAR filesystem with `AccessDeniedException`. The check
explicitly rejects this internal compiler exception even when javac exits 0.
No successful complete Android build, APK installation, foreground behavior or
runtime installation is claimed for this staged change.

ADB failed locally before device communication:
`Cannot mkdir '\\.android': Permission denied`.
This does not establish whether phone ADB is currently on or off.

Backend start/stop/reconnection, interrupted installation recovery, per-session
workspace attachment, measured harness injection, DNS refresh, provider/model
acceptance and all seven complete journeys remain unfinished. Release rounds
remain 0/3. Root-only execution is not a restricted security sandbox.

## Resume

Apply the integration patch only after comparing its source-baseline hashes.
Run `scripts/stage-runtime-assets.py D:/TinyAgent-work/artifacts`,
`scripts/check-runtime-host.py`, then the canonical Android build/lint script.
Re-identify target Edge 40 serial ZY22HZPLL8 before installing the new APK.
Run clean installation and interruption/retry flows on device before acceptance.
Do not delete an incomplete root or reset app data to hide recovery failures.

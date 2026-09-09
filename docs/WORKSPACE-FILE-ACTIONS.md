# Workspace file actions

App-private Fedora paths are not Android Files locations. `/shared` is internal exchange storage, not public Downloads.

Tap a workspace file path in a conversation, including old inline-code paths. The app maps `/workspace/` and its own Android workspace path to a validated workspace-relative file. APK: install/save/share; ZIP: save/share; text/log: open/save/share; image/video: preview/save/share.

Save uses Android's document picker. Share grants read access to one FileProvider URI through Android's chooser. APK installation keeps the existing selected Stock/Developer/Root installation flow. Text preview is limited to 256 KiB; exports preserve the full file. Images decode at a sampled size. Video support depends on Android's installed codecs.

Dependency: `androidx.core:core:1.16.0` (Apache-2.0), AndroidX FileProvider. Its provider is not exported and exposes only `files/linux/workspace/`.

## 2026-09-09 Lyriq1 checks

- Target: ZY22J58799, app `io.github.gplaider.tinyagent.debug`; update installation preserves app data.
- Before: old blue inline workspace paths had no anchors (`evidence/artifact-links-before.json`).
- v29: anchors existed, but `_blank` navigation did not reach the native action handler. Switching the tested link to `_self` opened install/save/share. v30 routes local artifact link clicks in the current WebView, covering both inline paths and Markdown links.
- Native Save action exported Ventoid to `Download/Ventoid-lyriq1-export.apk`.
- Export SHA-256 equals the phone-built source: `dfc3104160b02f2b4ce237e6c2d8509674e1874777a0971a32c7c96e13058d0f` (23589632 bytes).
- Build, lint, app typecheck and `node scripts/check-artifact-links.mjs` passed.
- v30 installed with the existing signer; SHA-256 `cd4588474b51fba19b356f210e6413d962ce38e750148e5d8024234d95babe51`. Old Ventoid path opened the native menu on three consecutive Android touch tests. Android share chooser displayed the APK; cancelled without sending.
- Image/video playback and full share/install regression remain separate device checks; not claimed by the path/export test.

## v31 popup workflow

Artifact actions now use a rounded floating window over the existing conversation. Workspace install/export entry points also use a floating installer, while Android's own save picker and share chooser remain native system surfaces. Long names are limited to three lines and file sizes are human-readable.

Installed on Lyriq1 with the same signer, APK SHA-256 `fdcf60d40e870cfe5cd75bf0d29fd926021362f29cf30270d8709c2502ef061c`. Build/lint/runtime asset checks passed. Screenshot: `evidence/popup-v31.png`. Outside tap and Android Back both dismissed the popup; the session URL, dark setting and scroll offset `5132.7998046875` were unchanged (`popup-v31-before.json`, `popup-v31-after-outside.json`, `popup-v31-after-back.json`). Install settings opened as a floating window as well. No APK installation was triggered by this UI check.

## v32 touch-anchored menu

Replaces the centered large dialog with a 224dp popover at the path's touch position. One muted filename line and horizontal 48dp touch targets; APK actions are install/save/share. No dimming or close row. Screen-edge clamping keeps it on-screen; keyboard activation anchors to the link. Existing preview/install/export handlers remain intact.

Lyriq1 APK SHA-256 `6c6af95fe52fdbd4c42c460e437b5c786404d7c5fd4ab09f03750bba08a7809e`; same dev signer, update installed. Build/lint/assets and path boundary checks passed. Real taps at (300,450) and (900,750) produced different anchors, with the right-hand popover clamped inside the screen. `scripts/check-file-popover.py` verified the single horizontal action row on both (`evidence/popover-v32-top.json`, `popover-v32-right.json`). Outside-dismiss preserved the exact session URL, dark setting, and scroll offset 5888.7998046875. Screenshot: `evidence/popover-v32.png`.

## v33 direct install/save workflow

Selecting an existing artifact no longer opens the generic installer management form. Install immediately stages the selected APK using the saved installation authority, automatically opens Android's pending confirmation, and returns to the conversation on success/cancellation. Unknown-sources permission is requested only when needed. Save directly opens the system document picker and returns on completion/cancellation. Generic management remains available from Work environment.

Lyriq1 update SHA-256 `02f125b5e8c43226eb0b70c66a8335b8b9292e723af5d7d6459163a58700e9a6`; build/lint/packaged assets passed. Real path tap → Install opened the Android Ventoid update confirmation without another form. Cancel returned to the original conversation at scroll offset 5132.7998046875, with dark setting unchanged (`direct-v33-before.json`, `direct-v33-cancel.json`, `direct-v33-cancel.png`). No Ventoid update was performed by this check.

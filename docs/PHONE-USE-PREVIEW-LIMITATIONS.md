# Phone-use Preview: verified boundaries

## Integration candidate

Audit `85c4cef` is the base. Product phone-use (`89f53b3`, `6e840c5`) and the
opt-in Preview build (`4151071`) are integrated without reverting audited runtime,
workspace provider, native or version changes. APK production source: `a0a66b4`.
Commit `30ce727` changes only the isolated device test runners.

- Package: `io.github.gplaider.tinyagent.preview`
- Version: code 6, `0.0.1-alpha.2-rc.1`
- Release certificate SHA-256:
  `655e9ec3091f8f8426bf321f0e7fb3aa64dd72ab87b667476767c34b3f73e0bf`
- Candidate APK SHA-256:
  `b500224d9af9a4f980b7ad07fc1ff59201ba8c1a12ea4f05473d5090a9ac18ad`
- Rebuilt audited `libdnfastlaunch.so` SHA-256:
  `5e83132f0c250608bc2495d2611f0da052a4451170e6c6d751289bbd6ee4c6ba`

The fd-gate probe also cross-builds from audited source, but remains debug-only;
it is intentionally absent from the release APK. Audit GUI patch changes affect
only the session-access test fixture, so the verified cc8193f UI bytes are reused.

## Multiple installed variants

Main, debug and Preview have separate Android package IDs, private data, UIDs,
provider authorities and UID/PID-bound Android bridge sockets. This allows
side-by-side installation, not concurrent backends.

`LocalLinuxRuntime.startBackend()` and `LocalPolicy` hardcode
`http://127.0.0.1:4097` for every variant. Android app UIDs do not create separate
network namespaces. An existing listener occupies the candidate's endpoint; its
authentication also belongs to the other app. A launched settings activity or an
isolated probe on another port does not prove the candidate backend is ready.

Do not stop an existing app/job or reuse its credentials to make a Preview test
pass. Use separate-port lifecycle probes, or explicitly coordinate a temporary
stop and restore. A future concurrent-runtime implementation must route the
selected port through startup, health, notifications, WebView and URL policy;
changing only the server's command-line port is insufficient.

## Foldable phone-use

The bundled helper currently calls bare `screencap -p`, `uiautomator dump`, and
`input` commands. It does not record a display ID in snapshots or route capture,
UI trees and input to a measured display.

Earlier Flip7 SM-F766N measurements showed multiple physical displays. Bare
screencap emits a warning before the PNG. The helper correctly rejects the mixed
stream; stripping the warning would not prove matching capture/input targets.
Explicit host capture of physical main display `4633128672291735937` was only
installation QA, not product phone-use validation. Cover display
`4633128672291735938` input is not supported or validated.

The Flip is reserved for the user's separate build test during this campaign.
No fresh Flip capture, fold/unfold action or input is claimed. Four non-foldable
devices cannot establish foldable display routing support.

## Test interpretation

Keep these evidence levels distinct:

1. Host phone-use tests and Java installer tests cover helper guards and safe
   resource installation, not a live Android connection.
2. Android service/output probes use actual framework services and children,
   but the service fixture substitutes a sleep-backed runtime.
3. PRoot probes execute production runtime methods with pinned PRoot/Fedora.
4. Backend probes run shipped OpenCode on an ephemeral port and exercise shell
   cancellation/recovery. They do not invoke full service prepare, Android
   pairing, phone input, a model or package transactions.
5. Candidate install hashes and visible settings prove install/launch only.
   Full candidate preparation and product phone-use require separate evidence.

Earlier product phone-use capture/tap on Edge ZY22HZPLL8 used the same helper
bytes as this integration. That evidence does not prove a fresh Preview pairing
or phone-use on each device in this campaign.

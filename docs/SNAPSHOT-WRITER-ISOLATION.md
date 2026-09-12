# Snapshot writer isolation candidate

Runtime `1.18.29-tinyagent.4` separates serialized immutable full-diff reads
from snapshot index mutations. A slow diff no longer holds the writer semaphore.
Garbage collection acquires the diff semaphore before the writer semaphore, so
object pruning cannot overlap a diff read. Mutating operations remain serialized.

The actual service regression gates `git cat-file --batch`: the old implementation
fails with `snapshot writer blocked behind diff reader`; the corrected version
stores a new snapshot, retains the original diff, and delays GC until the reader
is released. Snapshot regression: 54 pass, 3 Windows platform skips, 0 failures.
The expanded concurrency check and package typecheck pass. Startup recovery and
server-wide status regressions also pass.

ARM binary SHA256: `f54988bd412acf11d271f2935bd6cbfff043ee31ee679c5948d0871c280c7426`.
Archive SHA256: `e2cf56960cd6ec21707a096f87a5af43529f3d5a7a16786ad83b52ef761f6857`.
The full patch and source paths are recorded in `runtime/opencode-snapshot-4.json`.
Apply `runtime/opencode-snapshot-4.patch` to the pinned upstream commit. Use Bun
1.3.14, `OPENCODE_VERSION=1.18.29-tinyagent.4`, `OPENCODE_CHANNEL=latest`, empty
`OPENCODE_RELEASE`, pinned `MODELS_DEV_API_JSON=runtime/models-runtime-recovery-1.json`,
and `OPENCODE_COMPILE_EXECUTABLE` pointing to the official ARM64 Bun executable.
From `packages/opencode`, run `bun run script/build.ts --target=opencode-linux-arm64
--skip-install --skip-embed-web-ui`, preserving any previous dist binary first.
Package with `scripts/package-opencode-runtime.py`, then stage the archive with
`scripts/stage-runtime-assets.py --opencode-archive` and build the APK normally.

Pacman production APK update passed with the existing signing certificate,
conversation and provider preserved. DeepSeek V4.1 Flash executed the installed
ARM binary: version and SHA256 matched above, both commands exited zero. It wrote
and edited `/workspace/snapshot4-smoke/probe.txt`; tapping the returned path opened
the file actions and the preview showed `after`. The app retained Android UID10227.
Evidence: `evidence/snapshot4-apk-candidate.json` and `snapshot4-tool-*.xml`.
The deterministic gated diff concurrency regression remains host-only. This does
not prove every observed device slowdown had this cause or replace long-build tests.

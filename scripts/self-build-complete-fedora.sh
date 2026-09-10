#!/usr/bin/bash
# Development acceptance runner. Every compile below runs in the app-owned phone Fedora.
set -eu
test "${TINYAGENT_EXECUTION_PROVIDER:-}" = fedora-local
test "$(uname -m)" = aarch64
source=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
test -f "$source/app/build.gradle.kts"
trap 'status=$?; printf "tinyagent_self_build_exit=%s\n" "$status"' EXIT
printf 'environment=%s\ncwd=%s\npid=%s\n' "$TINYAGENT_EXECUTION_PROVIDER" "$source" "$$"
cd "$source"
/usr/bin/bash scripts/prepare-development.sh
git rev-parse HEAD
git diff --stat
python3 scripts/collect_upstream.py
python3 scripts/prepare-fedora.py artifacts
python3 scripts/stage-runtime-assets.py artifacts
python3 scripts/stage-proot.py
python3 scripts/collect-proot-sources.py
python3 scripts/build-dnfast-launcher.py

tools=/opt/tinyagent-build
archive=$tools/bun-1.3.14-arm64.zip
if test ! -f "$archive"; then
  curl -fsSL --retry 2 --max-time 600 -o "$archive.part" https://github.com/oven-sh/bun/releases/download/bun-v1.3.14/bun-linux-aarch64.zip
  printf 'a27ffb63a8310375836e0d6f668ae17fa8d8d18b88c37c821c65331973a19a3b  %s\n' "$archive.part" | sha256sum -c -
  mv "$archive.part" "$archive"
fi
printf 'a27ffb63a8310375836e0d6f668ae17fa8d8d18b88c37c821c65331973a19a3b  %s\n' "$archive" | sha256sum -c -
unzip -o "$archive" -d "$tools"
export PATH="$tools/bun-linux-aarch64:$PATH"
bun --version
upstream=/workspace/opencode-v1.18.29
if test ! -d "$upstream"; then
  git clone --depth 1 --branch v1.18.29 https://github.com/anomalyco/opencode.git "$upstream"
fi
test "$(git -C "$upstream" rev-parse HEAD)" = 16747470f976aca3d362ad730bcd3fe82ecc2c9a
if git -C "$upstream" apply --reverse --check "$source/patches/opencode-mobile-ux.patch" 2>/dev/null; then
  printf 'Mobile patch already applied.\n'
else
  git -C "$upstream" apply --check "$source/patches/opencode-mobile-ux.patch"
  git -C "$upstream" apply "$source/patches/opencode-mobile-ux.patch"
fi
cd "$upstream"
# Keep this cache separate from any prior hardlink/L2S installation. A poisoned
# hardlink cache can report success while leaving package directories empty.
# The GUI does not need the CLI native addon install scripts.
mkdir -p node_modules
bun install --frozen-lockfile --backend copyfile --cache-dir "$tools/bun-copy-clean-cache" --filter '@opencode-ai/app' --ignore-scripts
cd packages/app
node node_modules/vite/bin/vite.js build
cd "$source"
python3 scripts/stage-web-ui.py "$upstream"
/usr/bin/bash scripts/build-android-fedora.sh
python3 scripts/check-packaged-runtime.py
sha256sum app/build/outputs/apk/debug/app-debug.apk
printf 'TinyAgent APK compiled from source inside phone Fedora. Signing/update acceptance remains separate.\n'

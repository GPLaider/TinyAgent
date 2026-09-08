#!/usr/bin/bash
set -eu
trap 'status=$?; printf "phone_clean_cache_build_exit=%s\n" "$status"' EXIT
test "${TINYAGENT_EXECUTION_PROVIDER:-}" = fedora-local
cd /workspace/opencode-v1.18.29
python3 - <<'PY'
import os, pathlib, tempfile
root = pathlib.Path.cwd().resolve()
workspace = pathlib.Path('/workspace').resolve()
assert root == workspace / 'opencode-v1.18.29'
backup = pathlib.Path(tempfile.mkdtemp(prefix='opencode-failed-deps-', dir=workspace))
for current, directories, _ in os.walk(root, topdown=True, followlinks=False):
    directories[:] = [name for name in directories if name != '.git']
    if 'node_modules' not in directories: continue
    source = pathlib.Path(current) / 'node_modules'
    assert source.parent.resolve().is_relative_to(root)
    target = backup / source.relative_to(root)
    assert target.resolve().is_relative_to(backup)
    target.parent.mkdir(parents=True, exist_ok=True)
    source.rename(target)
    directories.remove('node_modules')
print('Failed generated dependencies retained at', backup)
PY
mkdir -p node_modules
/opt/tinyagent-build/bun-linux-aarch64/bun install --frozen-lockfile --backend copyfile --cache-dir /opt/tinyagent-build/bun-copy-clean-cache --filter '@opencode-ai/app' --filter '!./' --ignore-scripts
unset NODE_OPTIONS
/usr/bin/bash /workspace/build-phone-gui.sh

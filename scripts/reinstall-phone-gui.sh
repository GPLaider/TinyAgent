#!/usr/bin/bash
set -eu
trap 'status=$?; printf "phone_reinstall_exit=%s\n" "$status"' EXIT
test "${TINYAGENT_EXECUTION_PROVIDER:-}" = fedora-local
cd /workspace/opencode-v1.18.29
python3 - <<'PY'
import os, pathlib, shutil
root = pathlib.Path('/workspace/opencode-v1.18.29').resolve()
for current, directories, _ in os.walk(root, topdown=True, followlinks=False):
    directories[:] = [name for name in directories if name != '.git']
    if 'node_modules' not in directories:
        continue
    path = pathlib.Path(current) / 'node_modules'
    assert path.resolve().is_relative_to(root)
    print('Removing generated dependency directory:', path, flush=True)
    if path.is_symlink():
        path.unlink()
    else:
        shutil.rmtree(path)
    directories.remove('node_modules')
PY
export PATH=/opt/tinyagent-build/bun-linux-aarch64:$PATH
bun install --frozen-lockfile --backend copyfile --filter '@opencode-ai/app' --filter '!./' --ignore-scripts
/usr/bin/bash /workspace/build-phone-gui.sh

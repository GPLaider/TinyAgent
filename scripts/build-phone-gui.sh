#!/usr/bin/bash
set -eu
trap 'status=$?; printf "phone_gui_exit=%s\n" "$status"' EXIT
test "${TINYAGENT_EXECUTION_PROVIDER:-}" = fedora-local
microdnf install -y nodejs
node --version
cd /workspace/opencode-v1.18.29/packages/app
node node_modules/vite/bin/vite.js build
cd /workspace/tinyagent-self-build-940bc9b
python3 scripts/stage-web-ui.py /workspace/opencode-v1.18.29
/usr/bin/bash scripts/build-android-fedora.sh
python3 scripts/check-packaged-runtime.py
sha256sum app/build/outputs/apk/debug/app-debug.apk

#!/usr/bin/bash
set -eu
trap 'status=$?; printf "phone_symlink_build_exit=%s\n" "$status"' EXIT
test "${TINYAGENT_EXECUTION_PROVIDER:-}" = fedora-local
cd /workspace/opencode-v1.18.29
export PATH=/opt/tinyagent-build/bun-linux-aarch64:$PATH
bun install --frozen-lockfile --backend symlink --cache-dir /opt/tinyagent-build/bun-copy-clean-cache --filter '@opencode-ai/app' --filter '!./' --ignore-scripts --force
export NODE_OPTIONS='--preserve-symlinks --preserve-symlinks-main'
/usr/bin/bash /workspace/build-phone-gui.sh

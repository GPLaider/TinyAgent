#!/usr/bin/bash
set -eu
trap 'status=$?; printf "bun_copy_probe_exit=%s\n" "$status"' EXIT
test "${TINYAGENT_EXECUTION_PROVIDER:-}" = fedora-local
mkdir -p /workspace/bun-copy-probe-2
cd /workspace/bun-copy-probe-2
printf '{"name":"tinyagent-copy-probe","private":true,"dependencies":{"vite":"7.1.4"}}\n' > package.json
mkdir -p node_modules
/opt/tinyagent-build/bun-linux-aarch64/bun install --backend copyfile --cache-dir /opt/tinyagent-build/bun-copy-clean-cache --ignore-scripts
test -f node_modules/vite/package.json
test -f node_modules/vite/bin/vite.js
node node_modules/vite/bin/vite.js --version

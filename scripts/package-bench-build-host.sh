#!/usr/bin/bash
set -eu
work="$HOME/tinyagent-package-bench-20260909"
mkdir -p "$work/source" "$work/output"
test ! -f "$work/source/Cargo.toml"
tar -xf /tmp/tinyagent-dnfast-35d4a1b.tar -C "$work/source"
cp /tmp/package-bench-build-arm64.sh "$work/build.sh"
podman run --name tinyagent-dnfast-arm64-20260909 --network=host -v "$work:/work:Z" registry.fedoraproject.org/fedora:44 /usr/bin/bash /work/build.sh

#!/usr/bin/bash
set -eu
uname -m
cat /etc/fedora-release
getconf _NPROCESSORS_ONLN
df -h /tmp "$HOME"
free -m
for tool in cargo rustc gcc pkg-config podman; do command -v "$tool" || true; done
rpm -q libsolv-devel rpm-devel libmodulemd-devel openssl-devel zstd-devel

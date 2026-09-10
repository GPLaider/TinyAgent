#!/usr/bin/bash
set -eu
dnf5 --repo=fedora --setopt=fedora.metalink= --setopt=fedora.baseurl=https://ftp.yz.yamagata-u.ac.jp/pub/linux/fedora-projects/fedora/linux/releases/44/Everything/aarch64/os/ install -y patchelf python3 tar gzip
mkdir -p /work/direct
tar -xzf /work/original.tar.gz -C /work/direct
cd /work/direct
for binary in dnfast/bin/dnfast dnfast/bin/dnfast-executor; do
    patchelf --set-interpreter "$DNFAST_GUEST_ROOT/dnfast/lib/ld-linux-aarch64.so.1" --force-rpath --set-rpath '$ORIGIN/../lib' "$binary"
    patchelf --print-interpreter "$binary"
    patchelf --print-rpath "$binary"
done
python3 /work/package-direct.py
tar -czf /work/dnfast-direct-arm64.tar.gz dnfast
sha256sum /work/dnfast-direct-arm64.tar.gz

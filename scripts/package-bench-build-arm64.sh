#!/usr/bin/bash
set -eu
test "$(uname -m)" = aarch64
dnf5 install -y cargo rust gcc gcc-c++ make cmake pkgconf-pkg-config libsolv-devel rpm-devel libmodulemd-devel openssl-devel libzstd-devel clang-devel nettle-devel bzip2-devel libxml2-devel curl cpio python3 time
rpm -q libsolv-devel rpm-devel libmodulemd-devel dnf5
dnf5 downgrade -y --repo=fedora rpm rpm-libs rpm-build-libs rpm-devel
cd /work/source
export DNFAST_NATIVE_REAL=1
cargo build --locked --release -p dnfast-cli -p dnfast-executor
mkdir -p /work/output
cp target/release/dnfast target/release/dnfast-executor /work/output/
ldd /work/output/dnfast
dnf5 download --resolve --alldeps --destdir=/work/output/rpms microdnf
sha256sum /work/output/dnfast /work/output/dnfast-executor

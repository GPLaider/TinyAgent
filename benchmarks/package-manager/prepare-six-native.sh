#!/usr/bin/bash
set -eu
test "${TINYAGENT_EXECUTION_PROVIDER:-}" = fedora-local
test "$(uname -m)" = aarch64
base=/workspace/tinyagent-six-builds
exec 9>"$base/.native-preparation.lock"
flock -n 9
trap 'status=$?; printf "native_preparation_exit=%s\n" "$status"' EXIT
microdnf install -y cmake ninja-build meson pkgconf-pkg-config autoconf automake libtool \
  gettext-devel flex bison gperf protobuf-compiler patch zip xz bzip2 perl diffutils file which \
  clang clang-devel openssl-devel zlib-devel rustup procps-ng rsync
rpm -q --whatprovides cmake ninja-build meson pkgconf-pkg-config autoconf automake libtool gettext-devel \
  flex bison gperf protobuf-compiler patch zip xz bzip2 perl diffutils file which clang clang-devel \
  openssl-devel zlib-devel rustup procps-ng rsync > "$base/native-package-versions.txt"
export RUSTUP_HOME=/opt/tinyagent-build/rustup
export CARGO_HOME=/opt/tinyagent-build/cargo
export PATH="$CARGO_HOME/bin:$PATH"
if ! command -v rustup >/dev/null 2>&1; then
  rustup-init -y --no-modify-path --profile minimal --default-toolchain 1.85.0
fi
rustup toolchain install 1.85.0 --profile minimal --target aarch64-linux-android
rustup run 1.85.0 rustc --version
rustup run 1.85.0 cargo --version
printf 'Native host packages and Rust 1.85.0 ready\n'

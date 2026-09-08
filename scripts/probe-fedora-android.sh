#!/system/bin/sh
# Compatibility probe only. No mounts, service installation, or PreRoot replacement.
set -eu
umask 077
test "$(getprop ro.serialno)" = EDGE40_ROOT_SERIAL
test "$(id -u)" = 0
stage=/data/local/tmp/tinyagent-stage-20260908
root=/data/local/tmp/tinyagent-compat-20260908
test ! -e "$root"
test ! -L "$root"
test "$(sha256sum "$stage/fedora-44-arm64-rootfs.tar.gz" | cut -d ' ' -f 1)" = 3a3661a77d5fdb1e4bd10be484142683630c1ffb4c371931d46a42459fd4c125
test "$(sha256sum "$stage/opencode-linux-arm64.tar.gz" | cut -d ' ' -f 1)" = 70baf769395ca4e7a68924026530c390eace194f3b7e4919d4efcb2aa2eed3c0
mkdir -m 700 "$root"
tar -xzf "$stage/fedora-44-arm64-rootfs.tar.gz" -C "$root"
tar -xzf "$stage/opencode-linux-arm64.tar.gz" -C "$root/usr/local/bin"
printf 'Android UID: '
id
printf 'Fedora identity:\n'
chroot "$root" /usr/bin/cat /etc/os-release
chroot "$root" /usr/bin/bash --version
chroot "$root" /usr/bin/id
chroot "$root" /usr/bin/env -i HOME=/root PATH=/usr/local/bin:/usr/bin /usr/local/bin/opencode --version
printf 'Compatibility probe completed. No background backend was launched.\n'

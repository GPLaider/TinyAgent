#!/system/bin/sh
set -eu
test "$(getprop ro.serialno)" = EDGE40_ROOT_SERIAL
root=/data/local/tmp/tinyagent-compat-20260908
pid=$(pidof opencode)
case "$pid" in ''|*[!0-9]*) exit 1;; esac
test "$(readlink /proc/$pid/root)" = "$root"
printf 'serial=%s\ndevice=%s\nuid=%s\n' "$(getprop ro.serialno)" "$(getprop ro.product.device)" "$(id -u)" > "$root/workspace/android-device.txt"
cp /data/local/tmp/tinyagent-stage-20260908/probe-development-fedora.sh "$root/workspace/"
nsenter -t "$pid" -m -- chroot "$root" /usr/bin/env -i HOME=/root PATH=/usr/bin \
  /usr/bin/bash /workspace/probe-development-fedora.sh
printf 'Android reads back Fedora output:\n'
cat "$root/workspace/smoke-20260908/android-summary.json"

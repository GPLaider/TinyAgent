#!/system/bin/sh
set -eu
test "$(getprop ro.serialno)" = EDGE40_ROOT_SERIAL
root=/data/local/tmp/tinyagent-compat-20260908
pid=$(pidof opencode)
case "$pid" in ''|*[!0-9]*) exit 1;; esac
test "$(readlink /proc/$pid/root)" = "$root"
cp /data/local/tmp/tinyagent-stage-20260908/probe-public-provider.py "$root/workspace/probe-public-provider.py"
nsenter -t "$pid" -m -- chroot "$root" /usr/bin/python3 /workspace/probe-public-provider.py "$@"

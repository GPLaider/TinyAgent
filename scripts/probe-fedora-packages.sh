#!/system/bin/sh
set -eu
test "$(getprop ro.serialno)" = EDGE40_ROOT_SERIAL
root=/data/local/tmp/tinyagent-compat-20260908
pid=$(pidof opencode)
case "$pid" in ''|*[!0-9]*) exit 1;; esac
test "$(readlink /proc/$pid/root)" = "$root"
# Measured from this phone's active VPN and cellular LinkProperties, 2026-09-08.
# Production setup must refresh DNS when the selected Android network changes.
test ! -L "$root/etc/resolv.conf"
printf 'nameserver 100.100.100.100\nnameserver 116.98.212.54\noptions timeout:2 attempts:2\n' > "$root/etc/resolv.conf"
nsenter -t "$pid" -m -- chroot "$root" /usr/bin/curl -fsSL --max-time 25 \
  -o /dev/null -w 'Fedora HTTPS status=%{http_code}\n' https://fedoraproject.org/
nsenter -t "$pid" -m -- chroot "$root" /usr/bin/env -i HOME=/root PATH=/usr/bin \
  /usr/bin/microdnf install -y git python3 make gcc

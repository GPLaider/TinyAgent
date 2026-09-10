#!/system/bin/sh
set -eu
test "$(getprop ro.serialno)" = ZY22HZPLL8
root=/data/local/tinyagent/runtime/0.1.2/rootfs
read -r pid started boot < /data/local/tinyagent/run/backend.state
case "$pid" in ''|*[!0-9]*) exit 1;; esac
test "$(readlink /proc/$pid/root)" = "$root"
# Print only the permission object; provider credentials never enter the report.
permission=$(nsenter -t "$pid" -m -- chroot "$root" /usr/bin/curl --max-time 10 -fsS \
  --user "opencode:$(cat /data/local/tinyagent/data/.tinyagent-server-password)" \
  http://127.0.0.1:4096/config | grep -o '"permission":{[^}]*}')
test "$permission" = '"permission":{"*":"allow"}'
printf '%s\n' "$permission"

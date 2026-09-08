#!/system/bin/sh
set -eu
test "$(getprop ro.serialno)" = EDGE40_ROOT_SERIAL
root=/data/local/tmp/tinyagent-compat-20260908
pid=$(pidof opencode)
case "$pid" in ''|*[!0-9]*) echo 'Expected exactly one diagnostic backend' >&2; exit 1;; esac
test "$(readlink /proc/$pid/root)" = "$root"
test "$(readlink /proc/$pid/cwd)" = "$root/workspace"
printf 'device=EDGE40_ROOT_SERIAL pid=%s\nroot=' "$pid"
readlink "/proc/$pid/root"
printf 'cwd='
readlink "/proc/$pid/cwd"
printf 'namespace='
readlink "/proc/$pid/ns/mnt"
status=$(nsenter -t "$pid" -m -- chroot "$root" /usr/bin/curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:4096/global/health)
test "$status" = 401
printf 'unauthenticated_status=%s\nauthenticated_health=' "$status"
nsenter -t "$pid" -m -- chroot "$root" /usr/bin/curl -fsS \
  --user "opencode:$(cat "$root/root/.tinyagent-server-password")" http://127.0.0.1:4096/global/health
printf '\n'

#!/system/bin/sh
set -eu
test "$(getprop ro.serialno)" = ZY22HZPLL8
test "$(id -u)" = 0
root=/data/local/tinyagent/runtime/0.1.0/rootfs
manager=/data/local/tmp/tinyagent-preroot-0.1.0/backend.sh
case "${1:-}" in
  switch)
    old=$(pidof opencode || true)
    case "$old" in ''|*[!0-9]*) echo 'Expected one diagnostic backend' >&2; exit 1;; esac
    test "$(readlink /proc/$old/root)" = /data/local/tmp/tinyagent-compat-20260908
    kill -TERM "$old"
    for attempt in 1 2 3 4 5; do
      test -d "/proc/$old" || break
      sleep 1
    done
    test ! -d "/proc/$old"
    ;;
  start) ;;
  stop)
    /system/bin/sh "$manager" unrestricted-root stop
    exit
    ;;
  *) exit 1;;
esac
/system/bin/sh "$manager" unrestricted-root start
read -r pid started boot < /data/local/tinyagent/run/backend.state
test "$(readlink /proc/$pid/root)" = "$root"
test "$(readlink /proc/$pid/cwd)" = "$root/workspace"
grep '^PPid:' "/proc/$pid/status"
readlink "/proc/$pid/ns/mnt"
status=0
for attempt in 1 2 3 4 5 6 7 8 9 10; do
  status=$(nsenter -t "$pid" -m -- chroot "$root" /usr/bin/curl --max-time 2 -s -o /dev/null \
    -w '%{http_code}' http://127.0.0.1:4096/global/health) || true
  test "$status" != 401 || break
  sleep 1
done
test "$status" = 401
printf 'unauthenticated=401\nauthenticated='
nsenter -t "$pid" -m -- chroot "$root" /usr/bin/curl --max-time 5 -fsS \
  --user "opencode:$(cat /data/local/tinyagent/data/.tinyagent-server-password)" http://127.0.0.1:4096/global/health
printf '\n'
test -z "$(grep "$root" /proc/mounts || true)"
sha256sum /data/local/tinyagent/workspaces/setup-preservation-marker.txt

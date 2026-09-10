#!/system/bin/sh
# Root-owned backend state survives loss of an ADB connection or Activity.
set -eu
umask 077
fail() { printf 'PreRoot: %s\n' "$*" >&2; exit 1; }
test "$(id -u)" = 0 || fail 'root ADB is required'
test "$#" -eq 2 || fail 'usage: backend.sh unrestricted-root start|status|stop'
test "$1" = unrestricted-root || fail 'unsupported permission mode'
action=$2
case "$action" in start|status|stop) ;; *) fail 'unknown action';; esac
base=/data/local/tinyagent
root="$base/runtime/0.1.2/rootfs"
test "$(realpath "$root")" = "$root" || fail 'prepared root must be canonical'
test -x "$root/usr/local/bin/opencode" || fail 'backend is not prepared'
for directory in data run; do
  test "$(realpath "$base/$directory")" = "$base/$directory" || fail 'non-canonical state directory'
  test "$(stat -c %u "$base/$directory")" = 0 || fail 'state must be root-owned'
done
exec 9> "$base/run/backend.lock"
# Android mksh closes high descriptors on exec unless inheritance is explicit.
flock -n 9 9>&9 || fail 'another backend operation is active'
state="$base/run/backend.state"
boot=$(cat /proc/sys/kernel/random/boot_id)
birth() {
  test -r "/proc/$1/stat" || return 1
  line=$(cat "/proc/$1/stat") || return 1
  line=${line##*) }
  set -- $line
  test "$#" -ge 20 || return 1
  shift 19
  printf '%s\n' "$1"
}
live() {
  test -f "$state" || return 1
  read -r pid started recorded_boot < "$state" || return 1
  case "$pid:$started" in *[!0-9:]*|:*|*:) return 1;; esac
  test "$pid" -gt 1 && test "$recorded_boot" = "$boot" || return 1
  test "$(birth "$pid")" = "$started" || return 1
  test "$(readlink "/proc/$pid/root")" = "$root" || return 1
}
if test "$action" = status; then
  if live; then printf 'state=running pid=%s start=%s\n' "$pid" "$started"
  else printf 'state=stopped-or-unverified\n'; fi
  exit 0
fi
if test "$action" = stop; then
  live || fail 'no verified backend to stop'
  # setsid establishes a dedicated process group; never signal a reused PID.
  line=$(cat "/proc/$pid/stat")
  line=${line##*) }
  set -- $line
  test "$3" = "$pid" || fail 'backend no longer leads its process group'
  kill -TERM -- "-$pid"
  for attempt in 1 2 3 4 5; do
    if ! live && ! kill -0 -- "-$pid" 2>/dev/null; then printf 'state=stopped\n'; exit 0; fi
    sleep 1
  done
  fail 'backend did not exit after TERM; inspect processes before retrying'
fi
if live; then printf 'state=running pid=%s start=%s\n' "$pid" "$started"; exit 0; fi
# A stale or unexpected process record must not trigger a second server silently.
if test -f "$state"; then
  read -r old_pid old_start old_boot < "$state" || fail 'malformed previous state'
  case "$old_pid" in ''|*[!0-9]*) fail 'invalid previous PID';; esac
  if test "$old_boot" = "$boot" && test "$(birth "$old_pid" || true)" = "$old_start"; then
    fail 'previous process identity is uncertain'
  fi
fi
password_file="$base/data/.tinyagent-server-password"
if test ! -f "$password_file"; then
  od -An -N32 -tx1 /dev/urandom | tr -d ' \n' > "$password_file"
fi
test ! -L "$password_file" || fail 'password must not be a symlink'
chmod 600 "$password_file"
password=$(cat "$password_file")
case "$password" in ''|*[!0-9a-f]*) fail 'invalid password';; esac
test "${#password}" -eq 64 || fail 'invalid password length'
scripts=$(dirname "$(realpath "$0")")
# Closing descriptor 9 prevents the detached server retaining the operation lock.
nohup setsid /system/bin/sh "$scripts/preroot.sh" "$root" unrestricted-root serve \
  </dev/null >>"$base/run/backend.log" 2>&1 9>&- &
pid=$!
started=$(birth "$pid") || fail 'server launcher exited immediately'
printf '%s %s %s\n' "$pid" "$started" "$boot" > "$state.pending"
mv "$state.pending" "$state"
for attempt in 1 2 3 4 5; do
  if live; then printf 'state=running pid=%s start=%s\n' "$pid" "$started"; exit 0; fi
  sleep 1
done
fail 'server did not enter the prepared root; inspect backend.log'

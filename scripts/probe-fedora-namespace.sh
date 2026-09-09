#!/system/bin/sh
# Run only via: unshare -m /system/bin/sh THIS_FILE
set -eu
test "$(getprop ro.serialno)" = ZY22HZPLL8
test "$(id -u)" = 0
test "$(readlink /proc/self/ns/mnt)" != "$(readlink /proc/$PPID/ns/mnt)"
root=/data/local/tmp/tinyagent-compat-20260908
test -f "$root/usr/local/bin/opencode"
# Toybox uses -o rslave and two operands; a type avoids its bind/fstab autodetection.
# Propagation flags are handled by mount(2) before filesystem type lookup.
mount -t tmpfs -o rslave none /
if grep -q ' shared:' /proc/self/mountinfo; then
  echo 'Mount propagation remains shared; refusing compatibility mounts.' >&2
  exit 1
fi
mount -t proc proc "$root/proc"
mount --bind /dev "$root/dev"
printf 'Isolated mount namespace: '
readlink /proc/self/ns/mnt
if test "${1:-version}" = serve; then
  umask 077
  password_file="$root/root/.tinyagent-server-password"
  if test ! -f "$password_file"; then
    od -An -N32 -tx1 /dev/urandom | tr -d ' \n' > "$password_file"
  fi
  test "$(wc -c < "$password_file")" -eq 64
  mkdir -p "$root/workspace"
  exec chroot "$root" /usr/bin/env -i -C /workspace HOME=/root PATH=/usr/local/bin:/usr/bin TMPDIR=/tmp \
    OPENCODE_SERVER_PASSWORD="$(cat "$password_file")" \
    /usr/local/bin/opencode serve --hostname 127.0.0.1 --port 4096
fi
chroot "$root" /usr/bin/env -i HOME=/root PATH=/usr/local/bin:/usr/bin TMPDIR=/tmp /usr/local/bin/opencode --version

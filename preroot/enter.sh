#!/system/bin/sh
# Internal child of preroot.sh. Never mount in the calling Android namespace.
set -eu
test "$(id -u)" = 0
test "$#" -ge 3
test "$(readlink /proc/self/ns/mnt)" != "$(readlink /proc/$PPID/ns/mnt)"
root=$1
cwd=$2
shift 2
mount -t tmpfs -o rslave none /
if grep -q ' shared:' /proc/self/mountinfo; then
  echo 'PreRoot: shared propagation remains; refusing mounts' >&2
  exit 1
fi
mount -t proc proc "$root/proc"
mount --bind /dev "$root/dev"
if test "$root" = /data/local/tinyagent/runtime/0.1.2/rootfs; then
  base=/data/local/tinyagent
  for directory in data workspaces shared; do
    test -d "$base/$directory"
    test "$(realpath "$base/$directory")" = "$base/$directory"
    test "$(stat -c %u "$base/$directory")" = 0
  done
  # Backend credentials/database and workspaces outlive the versioned rootfs.
  mount --bind "$base/data" "$root/root"
  mount --bind "$base/workspaces" "$root/workspace"
  mount --bind "$base/shared" "$root/shared"
fi
if test "$1" = /usr/local/bin/opencode && test "${2:-}" = serve; then
  password=$(cat "$root/root/.tinyagent-server-password")
  case "$password" in ''|*[!0-9a-f]*) exit 1;; esac
  test "${#password}" -eq 64
  export OPENCODE_SERVER_PASSWORD="$password"
  # env -i is retained for ordinary commands; only the server receives this secret.
  exec chroot "$root" /usr/bin/env -i -C "$cwd" HOME=/root PATH=/usr/local/bin:/usr/bin TMPDIR=/tmp \
    OPENCODE_SERVER_PASSWORD="$password" OPENCODE_DISABLE_CHANNEL_DB=1 TINYAGENT_EXECUTION_PROVIDER=fedora-preroot \
    TINYAGENT_PERMISSION=unrestricted-root OPENCODE_CONFIG_CONTENT='{"permission":"allow"}' "$@"
fi
exec chroot "$root" /usr/bin/env -i -C "$cwd" \
  HOME=/root PATH=/usr/local/bin:/usr/bin TMPDIR=/tmp \
  TINYAGENT_EXECUTION_PROVIDER=fedora-preroot TINYAGENT_PERMISSION=unrestricted-root "$@"

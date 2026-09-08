#!/system/bin/sh
# Install only the pinned, previously audited archives into a fresh version.
set -eu
umask 077
fail() { printf 'PreRoot: %s\n' "$*" >&2; exit 1; }
test "$(id -u)" = 0 || fail 'root ADB is required'
test "$(getprop ro.product.cpu.abi)" = arm64-v8a || fail 'arm64 Android is required'
test "$#" -eq 2 || fail 'usage: prepare.sh FEDORA_LAYER OPENCODE_ARCHIVE'
fedora=$1
opencode=$2
for archive in "$fedora" "$opencode"; do
  case "$archive" in /data/*) ;; *) fail 'archive must be in Android /data';; esac
  test -f "$archive" && test ! -L "$archive" || fail 'archive must be a regular file'
  test "$(realpath "$archive")" = "$archive" || fail 'archive path must be canonical'
done
verify() {
  actual=$(sha256sum "$1")
  test "${actual%% *}" = "$2" || fail 'archive SHA256 mismatch'
}
base=/data/local/tinyagent
version=0.1.0
mkdir -p "$base"
test "$(realpath "$base")" = "$base" || fail 'installation path is not canonical'
test "$(stat -c %u "$base")" = 0 || fail 'installation must be root-owned'
chmod 700 "$base"
# Never reuse a failed staging tree or overwrite an installed version.
for directory in runtime data workspaces shared run; do
  test ! -L "$base/$directory" || fail 'installation subdirectory is a symlink'
  mkdir -p "$base/$directory"
  test "$(stat -c %u "$base/$directory")" = 0 || fail 'installation subdirectory is not root-owned'
  chmod 700 "$base/$directory"
done
target="$base/runtime/$version"
if test -e "$target" || test -L "$target"; then
  test "$(realpath "$target")" = "$target" || fail 'installed version is not canonical'
  test "$(stat -c %u "$target")" = 0 || fail 'installed version is not root-owned'
  test -f "$target/versions" || fail 'installed version metadata is missing'
  test "$(cat "$target/versions")" = "$(printf 'preroot=%s\nfedora=44\nopencode=1.18.29\n' "$version")" || fail 'installed version metadata differs'
  test -x "$target/rootfs/usr/local/bin/opencode" || fail 'installed backend is missing'
  printf 'phase=prepared root=%s/rootfs\n' "$target"
  exit 0
fi
stage="$base/runtime/$version.pending"
mkdir "$stage" || fail 'unfinished installation exists; inspect it before retrying'
# Snapshot app-owned inputs into the root-only staging directory before hashing
# and extracting. An app write after verification must not change extracted bytes.
for archive in "$fedora" "$opencode"; do
  test "$(stat -c %s "$archive")" -le 65000000 || fail 'archive exceeds size limit'
done
cp "$fedora" "$stage/fedora.tar.gz"
cp "$opencode" "$stage/opencode.tar.gz"
verify "$stage/fedora.tar.gz" 3a3661a77d5fdb1e4bd10be484142683630c1ffb4c371931d46a42459fd4c125
verify "$stage/opencode.tar.gz" 70baf769395ca4e7a68924026530c390eace194f3b7e4919d4efcb2aa2eed3c0
printf 'phase=verified\n'
# Failures retain staging for diagnosis; they never erase data or prior versions.
mkdir "$stage/rootfs"
printf 'phase=extracting-fedora\n'
tar -xzf "$stage/fedora.tar.gz" -C "$stage/rootfs"
test -f "$stage/rootfs/etc/fedora-release" || fail 'Fedora identity is missing'
mkdir -p "$stage/rootfs/usr/local/bin"
printf 'phase=extracting-opencode\n'
tar -xzf "$stage/opencode.tar.gz" -C "$stage/rootfs/usr/local/bin"
test -x "$stage/rootfs/usr/local/bin/opencode" || fail 'OpenCode binary is missing'
mkdir -p "$stage/rootfs/workspace" "$stage/rootfs/shared"
printf 'preroot=%s\nfedora=44\nopencode=1.18.29\n' "$version" > "$stage/versions"
rm "$stage/fedora.tar.gz" "$stage/opencode.tar.gz"
mv "$stage" "$target"
printf 'phase=prepared root=%s/rootfs\n' "$target"

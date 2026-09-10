#!/usr/bin/bash
set -eu
revision=${1:-206cfc7}
case "$revision" in
206cfc7) source=/home/admin/dnfast-diagnostic-01a08398/dnfast-diagnostic-arm64.tar.gz; expected=e5ada839dec58f79a5f674ca82186534ad1d4692d8e4f3726d5adc8ef10f84cc ;;
03d6430) source=/home/admin/dnfast-rename-final-01a08398/dnfast-rename-arm64.tar.gz; expected=88e696f667b03a51402ccf8ead501cdb5126606745ee2a4a10b4f796f2663daf ;;
5313ef6) source=/home/admin/dnfast-eacces-01a08398/dnfast-eacces-arm64.tar.gz; expected=77889ca6e2137b923c8e81099fd535af10df3e469a3bc1544d459bd1f3d28456 ;;
4717e11) source=/home/admin/dnfast-verity-01a08398/dnfast-verity-arm64.tar.gz; expected=edfd0ccb3012b62a9234a877dfc9c0b673aeac4d9c7eddff0c0cd9f57fb694c4 ;;
*) exit 2 ;;
esac
work=/home/admin/tinyagent-direct-$revision
mkdir -p "$work"
cp "$source" "$work/original.tar.gz"
cd "$work"
rpm -Kv /home/admin/tinyagent-direct-206cfc7/patchelf.rpm
mkdir -p tooling direct
cd tooling
rpm2cpio /home/admin/tinyagent-direct-206cfc7/patchelf.rpm | cpio -idm --no-absolute-filenames
cd "$work"
test "$(sha256sum original.tar.gz | cut -d ' ' -f 1)" = "$expected"
tar -xzf original.tar.gz -C direct
export DNFAST_GUEST_ROOT=/workspace/tinyagent-package-bench-20260909/fixed-$revision-direct
for binary in direct/dnfast/bin/dnfast direct/dnfast/bin/dnfast-executor; do
    tooling/usr/bin/patchelf --set-interpreter "$DNFAST_GUEST_ROOT/dnfast/lib/ld-linux-aarch64.so.1" --force-rpath --set-rpath '$ORIGIN/../lib' "$binary"
done
python3 /tmp/tinyagent-package-direct.py "$work/direct/dnfast"
tar -czf dnfast-direct-arm64.tar.gz -C direct dnfast
sha256sum dnfast-direct-arm64.tar.gz
cp dnfast-direct-arm64.tar.gz "/home/admin/tinyagent-package-bench-20260909/output/dnfast-direct-$revision-arm64.tar.gz"

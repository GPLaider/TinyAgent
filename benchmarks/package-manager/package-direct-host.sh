#!/usr/bin/bash
set -eu
revision=${1:-e7d8030}
case "$revision" in
e7d8030) source=/home/admin/dnfast-final-01a08398/dnfast-fixed-arm64.tar.gz; expected=e6f409d07ae9e08fad4a546e16aed141dfe5a3d00bd631280a175d9595db6555 ;;
206cfc7) source=/home/admin/dnfast-diagnostic-01a08398/dnfast-diagnostic-arm64.tar.gz; expected=e5ada839dec58f79a5f674ca82186534ad1d4692d8e4f3726d5adc8ef10f84cc ;;
*) exit 2 ;;
esac
work=/home/admin/tinyagent-direct-$revision
mkdir -p "$work"
cp "$source" "$work/original.tar.gz"
test "$(sha256sum "$work/original.tar.gz" | cut -d ' ' -f 1)" = "$expected"
cp /tmp/tinyagent-package-direct.sh "$work/package-direct.sh"
cp /tmp/tinyagent-package-direct.py "$work/package-direct.py"
podman run --rm --name "tinyagent-package-direct-$revision" -e "DNFAST_GUEST_ROOT=/workspace/tinyagent-package-bench-20260909/fixed-$revision-direct" -v "$work:/work:Z" registry.fedoraproject.org/fedora:44 /usr/bin/bash /work/package-direct.sh
cp "$work/dnfast-direct-arm64.tar.gz" "/home/admin/tinyagent-package-bench-20260909/output/dnfast-direct-$revision-arm64.tar.gz"

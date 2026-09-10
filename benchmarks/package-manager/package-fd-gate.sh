#!/usr/bin/bash
set -eu
cd /home/admin/tinyagent-package-bench-20260909/output
test "$(sha256sum fd-gate-linux | cut -d ' ' -f 1)" = dd9b7090c74c1d69f247841f6a2ad613ead75e1147b89ddf76fd6d3b60f449f7
cp fd-gate-linux fd-gate-linux-direct
libs=/workspace/tinyagent-package-bench-20260909/fixed-4717e11-direct/dnfast/lib
/home/admin/tinyagent-direct-206cfc7/tooling/usr/bin/patchelf --set-interpreter "$libs/ld-linux-aarch64.so.1" --force-rpath --set-rpath "$libs" fd-gate-linux-direct
sha256sum fd-gate-linux-direct
test "$(sha256sum fd-roundtrip-linux | cut -d ' ' -f 1)" = c47b1b374a8863bba024497e22f9891f4fb56861f9143fc781065b12314d9709
cp fd-roundtrip-linux fd-roundtrip-linux-direct
/home/admin/tinyagent-direct-206cfc7/tooling/usr/bin/patchelf --set-interpreter "$libs/ld-linux-aarch64.so.1" --force-rpath --set-rpath "$libs" fd-roundtrip-linux-direct
sha256sum fd-roundtrip-linux-direct
test "$(sha256sum fd-app-anon-linux-original | cut -d ' ' -f 1)" = 4399fd4942d8245e67ce2be1e3acdd3844b3bf115abb90431ac5cb499eafe2dc
cp fd-app-anon-linux-original fd-app-anon-linux
/home/admin/tinyagent-direct-206cfc7/tooling/usr/bin/patchelf --set-interpreter "$libs/ld-linux-aarch64.so.1" --force-rpath --set-rpath "$libs" fd-app-anon-linux
sha256sum fd-app-anon-linux
test "$(sha256sum fd-app-proot-linux-original | cut -d ' ' -f 1)" = a5b4966a0fccd8837ce95d4922444ecd7d5425ad9f9682f3e40fbfd1a6a47f25
cp fd-app-proot-linux-original fd-app-proot-linux
/home/admin/tinyagent-direct-206cfc7/tooling/usr/bin/patchelf --set-interpreter "$libs/ld-linux-aarch64.so.1" --force-rpath --set-rpath "$libs" fd-app-proot-linux
sha256sum fd-app-proot-linux

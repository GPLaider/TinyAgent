"""Build the Android launcher with the pinned installed NDK; no shell source."""
import hashlib
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
compiler = Path.home() / 'AppData/Local/Android/Sdk/ndk/28.0.13004108/toolchains/llvm/prebuilt/windows-x86_64/bin/clang.exe'
output = root / 'app/src/debug/jniLibs/arm64-v8a/libdnfastlaunch.so'
output.parent.mkdir(parents=True, exist_ok=True)
subprocess.run([str(compiler), '--target=aarch64-linux-android30', '-std=c11', '-O2',
                '-Wall', '-Wextra', '-Werror', '-Wl,-z,max-page-size=16384',
                str(root / 'native/dnfast-launch.c'), '-o', str(output)], check=True)
print(hashlib.sha256(output.read_bytes()).hexdigest(), output.name)

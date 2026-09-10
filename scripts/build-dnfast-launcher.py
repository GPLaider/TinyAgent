"""Build the Android launcher with the pinned installed NDK; no shell source."""
import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
if os.name == 'nt':
    compiler = Path.home() / 'AppData/Local/Android/Sdk/ndk/28.0.13004108/toolchains/llvm/prebuilt/windows-x86_64/bin/clang.exe'
else:
    assert os.uname().machine == 'aarch64'
    spec = importlib.util.spec_from_file_location('sdk_inputs', root/'scripts/prepare-android-sdk-fedora.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    archive = Path('/opt/tinyagent-build/extra-inputs/ndk29.tar.xz')
    archive.parent.mkdir(parents=True, exist_ok=True)
    helper.download('https://github.com/HomuHomu833/android-ndk-custom/releases/download/r29/android-ndk-r29-aarch64-linux-musl.tar.xz',
                    archive, 'sha256', 'fcc3b0ba65318317899fc296df0c5795d472a0cc3870b6fbf659939c1dde63ca', 192051660)
    helper.unpack(archive, archive.with_name(archive.name+'.unpacked'))
    compiler = archive.with_name(archive.name+'.unpacked')/'android-ndk-r29/toolchains/llvm/prebuilt/linux-arm64/bin/clang'
assert compiler.is_file()
for source, name in [('native/dnfast-launch.c', 'libdnfastlaunch.so'),
                     ('native/fd-gate/probe.c', 'libfdgate.so')]:
    output = root / 'app/src/debug/jniLibs/arm64-v8a' / name
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(compiler), '--target=aarch64-linux-android30', '-std=c11', '-O2',
                '-Wall', '-Wextra', '-Werror', '-Wl,-z,max-page-size=16384',
                str(root / source), '-o', str(output)], check=True)
    assert output.read_bytes()[18:20] == b'\xb7\x00', 'Expected ARM64 ELF'
    print(hashlib.sha256(output.read_bytes()).hexdigest(), output.name)

"""Build the Android launcher with the pinned installed NDK; no shell source."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
if os.name == 'nt':
    compiler = Path.home() / 'AppData/Local/Android/Sdk/ndk/28.0.13004108/toolchains/llvm/prebuilt/windows-x86_64/bin/clang.exe'
else:
    assert os.uname().machine == 'aarch64'
    config = json.loads(Path('/opt/tinyagent-build/extra-inputs/toolchains.json').read_text())
    compiler = Path(config['ndk_home'])/'toolchains/llvm/prebuilt/linux-arm64/bin/clang'
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

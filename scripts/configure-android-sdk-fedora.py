"""Assemble the pinned SDK layout and verify the ARM64 resource compiler."""
import json
import os
from pathlib import Path
import subprocess

assert os.environ.get('TINYAGENT_EXECUTION_PROVIDER') == 'fedora-local'
base = Path('/opt/tinyagent-build')
inputs = base / 'sdk-inputs'
sdk = base / 'android-sdk'
for name, target in [('platforms/android-36', inputs/'platform.zip.unpacked/android-36'),
                     ('build-tools/35.0.0', inputs/'build-tools.zip.unpacked/android-15'),
                     ('platform-tools', inputs/'arm64.tar.xz.unpacked/android-sdk/platform-tools')]:
    assert target.is_dir()
    link = sdk/name
    link.parent.mkdir(parents=True, exist_ok=True)
    if not link.exists(): link.symlink_to(target, target_is_directory=True)
    assert link.resolve() == target.resolve()
tools = list((inputs/'arm64.tar.xz.unpacked/android-sdk').rglob('aapt2'))
assert len(tools) == 1, tools
aapt2 = tools[0]
header = aapt2.read_bytes()[:64]
assert header[:4] == b'\x7fELF' and int.from_bytes(header[18:20], 'little') == 183
subprocess.run([str(aapt2), 'version'], check=True)
adb = sdk/'platform-tools/adb'
header = adb.read_bytes()[:64]
assert header[:4] == b'\x7fELF' and int.from_bytes(header[18:20], 'little') == 183
subprocess.run([str(adb), 'version'], check=True)
config = dict(android_home=str(sdk), aapt2=str(aapt2), java_home=str(base/'jdk-17.0.20.1+1'))
(base/'android-build.json').write_text(json.dumps(config, indent=2)+'\n')
print(json.dumps(config, indent=2))
print('sdk_config_exit=0')

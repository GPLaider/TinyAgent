"""Verify the downloaded ARM host compiler produces an Android ARM64 ELF."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

assert os.environ.get('TINYAGENT_EXECUTION_PROVIDER') == 'fedora-local'
assert os.uname().machine == 'aarch64'
config = json.loads(Path('/opt/tinyagent-build/extra-inputs/toolchains.json').read_text())
compiler = Path(config['ndk_home'])/'toolchains/llvm/prebuilt/linux-arm64/bin/aarch64-linux-android23-clang'
actual = (compiler.parent/'clang').resolve()
with actual.open('rb') as stream: header = stream.read(64)
assert header[:4] == b'\x7fELF' and int.from_bytes(header[18:20], 'little') == 183
version = subprocess.check_output([str(compiler), '--version'], stderr=subprocess.STDOUT).decode()
base = Path('/workspace/tinyagent-six-builds/native-toolchain-probe')
base.mkdir(exist_ok=True)
source = base/'hello.c'
source.write_text('#include <stdio.h>\nint main(void) { puts("TinyAgent Android ARM64"); return 0; }\n')
output = base/'hello-android-arm64'
command = [str(compiler), str(source), '-o', str(output)]
result = subprocess.run(command, capture_output=True, text=True)
report = dict(command=command, exit_code=result.returncode, output=result.stdout+result.stderr, compiler_version=version)
if result.returncode == 0:
    header = output.read_bytes()[:64]
    assert header[:4] == b'\x7fELF' and int.from_bytes(header[18:20], 'little') == 183
    report['sha256'] = hashlib.sha256(output.read_bytes()).hexdigest()
    report['scope'] = 'ARM64 host compiler produced Android ARM64 ELF; runtime execution not yet tested'
(base/'result.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report), flush=True)
raise SystemExit(result.returncode)

"""Use the already pinned ARM64 AIDL compiler in installed SDK build-tool versions."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile


def configure(sdk, compiler):
    with compiler.open('rb') as stream:
        header = stream.read(64)
    assert header[:4] == b'\x7fELF' and int.from_bytes(header[18:20], 'little') == 183, 'ARM64 AIDL required'
    changed = []
    for directory in sorted((sdk/'build-tools').iterdir()):
        target = directory/'aidl'
        if not directory.is_dir() or not target.exists():
            continue
        if target.resolve() != compiler.resolve():
            stage = directory/'.aidl-arm64-next'
            stage.unlink(missing_ok=True)
            stage.symlink_to(compiler)
            stage.replace(target)
        assert target.resolve() == compiler.resolve()
        changed.append(str(target))
    return changed


if __name__ == '__main__':
    assert os.environ.get('TINYAGENT_EXECUTION_PROVIDER') == 'fedora-local'
    assert os.uname().machine == 'aarch64'
    base = Path('/opt/tinyagent-build')
    config = json.loads((base/'android-build.json').read_text())
    compiler = Path(config['aapt2']).with_name('aidl')
    sdk = Path(config['android_home'])
    # Compile a real interface before changing any SDK path.
    with tempfile.TemporaryDirectory(prefix='tinyagent-aidl-') as directory:
        work = Path(directory)
        source = work/'tinyagent/check/ICheck.aidl'
        source.parent.mkdir(parents=True)
        source.write_text('package tinyagent.check; interface ICheck { int answer(); }\n')
        output = work/'ICheck.java'
        subprocess.run([str(compiler), str(source), str(output)], check=True)
        assert 'interface ICheck' in output.read_text()
    report = {'compiler': str(compiler), 'sha256': hashlib.sha256(compiler.read_bytes()).hexdigest(),
              'sdk_paths': configure(sdk, compiler), 'interface_compile': 'passed',
              'origin': 'Existing SHA256-pinned HomuHomu833 ARM64 SDK input; see sdk-inputs/provenance.json'}
    assert report['sdk_paths']
    (base/'arm-aidl.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report), flush=True)

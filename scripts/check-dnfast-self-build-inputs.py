"""Reuse shipped dnfast bytes in an isolated source tree; reject corrupt inputs."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

root = Path(__file__).resolve().parents[1]
apk = root / 'app/build/outputs/apk/debug/app-debug.apk'
with tempfile.TemporaryDirectory(prefix='tinyagent-dnfast-inputs-') as directory:
    fixture = Path(directory)
    (fixture / 'scripts').mkdir()
    script = fixture / 'scripts/stage-dnfast-runtime.py'
    shutil.copyfile(root / 'scripts/stage-dnfast-runtime.py', script)
    run = [sys.executable, str(script), '--installed-apk']
    subprocess.run([*run, str(apk)], check=True)
    assets = fixture / 'app/src/main/assets'
    names = ('dnfast-manifest.json', 'dnfast-root-overlay.tar.gz.bin')
    with zipfile.ZipFile(apk) as source:
        expected = {name: source.read('assets/' + name) for name in names}
    assert all((assets / name).read_bytes() == payload for name, payload in expected.items())
    for damaged in names:
        bad = fixture / 'bad.apk'
        with zipfile.ZipFile(bad, 'w') as target:
            for name, payload in expected.items():
                target.writestr('assets/' + name, b'corrupt' if name == damaged else payload)
        result = subprocess.run([*run, str(bad)], capture_output=True, text=True)
        assert result.returncode != 0 and 'hash mismatch' in result.stderr, result.stderr
        assert all((assets / name).read_bytes() == payload for name, payload in expected.items()), 'Rejected input replaced good assets'
print('PASS: installed APK reuse is byte-exact; corrupt manifest/overlay rejected without replacing good assets')

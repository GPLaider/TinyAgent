"""Independently copy and verify APKs from explicitly selected Pacman runs."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ADB = Path.home() / 'AppData/Local/Android/Sdk/platform-tools/adb.exe'
SERIAL = '000501423003390'
PACKAGE = 'io.github.gplaider.tinyagent.debug'

def adb(*args):
    return subprocess.check_output([str(ADB), '-s', SERIAL, *args], timeout=180)

assert adb('shell', 'getprop', 'ro.serialno').strip().decode() == SERIAL
for run in sys.argv[1:]:
    assert '/' not in run and '\\' not in run and '-build-' in run
    folder = ROOT / 'evidence/build-campaign' / run
    report = json.loads((folder / 'result.json').read_text())
    assert report['status'] == 'passed' and report['exit_code'] == 0
    assert b'BUILD SUCCESSFUL' in (folder / 'build.log').read_bytes()
    verified = []
    for apk in report['apks'] if 'apks' in report else [report['apk']]:
        path = apk['path']
        assert path.startswith('/workspace/tinyagent-six-builds/') and '..' not in Path(path).parts
        phone_path = 'files/linux' + path
        data = adb('exec-out', 'run-as', PACKAGE, 'cat', phone_path)
        checksum = hashlib.sha256(data).hexdigest()
        assert checksum == apk['sha256'] and len(data) == apk['size']
        assert adb('exec-out', 'run-as', PACKAGE, 'sha256sum', phone_path).decode().split()[0] == checksum
        dest = ROOT / 'artifacts/deepseek-campaign' / run / Path(path).name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        with zipfile.ZipFile(dest) as archive:
            assert 'AndroidManifest.xml' in archive.namelist()
            assert archive.testzip() is None
        verified.append(dict(apk, local_path=str(dest), zip_verified=True))
    assert verified
    result = dict(run=run, device=SERIAL, apks=verified,
                  scope='Fresh run log and phone/host hash and ZIP checks; no install or launch')
    (folder / 'independent-apk-verification.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(dict(run=run, verified_apks=len(verified))))

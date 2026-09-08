"""Install the verified phone-built development APK without clearing app data."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ADB = Path.home() / 'AppData/Local/Android/Sdk/platform-tools/adb.exe'
PACKAGE = 'io.github.gplaider.tinyagent.debug'
BASE = '/data/user/0/' + PACKAGE
APK = BASE + '/files/linux/workspace/tinyagent-self-build-940bc9b/app/build/outputs/apk/debug/app-debug.apk'
EXPECTED = 'abd22ba4fb37a0150138df2b3b2c7e85cbeebd4cd16a725831391e63d3b607a0'
def adb(*args):
    return subprocess.check_output([str(ADB), '-s', '192.0.2.2:5555', *args], timeout=180)
assert adb('shell', 'getprop', 'ro.serialno').decode().strip() == 'EDGE40_ROOT_SERIAL'
assert adb('shell', 'sha256sum', APK).decode().split()[0] == EXPECTED
def preserved():
    paths = [BASE + '/no_backup/stock-backend-auth', BASE + '/files/linux/workspace/model-c-probe-v11-20260908/main.c']
    return {p: hashlib.sha256(adb('exec-out', 'cat', p)).hexdigest() for p in paths}
before = preserved()
old = adb('shell', 'pm', 'path', PACKAGE).decode().strip().removeprefix('package:')
old_hash = adb('shell', 'sha256sum', old).decode().split()[0]
result = adb('shell', 'pm', 'install', '-r', APK).decode().strip()
assert result == 'Success', result
installed = adb('shell', 'pm', 'path', PACKAGE).decode().strip().removeprefix('package:')
assert adb('shell', 'sha256sum', installed).decode().split()[0] == EXPECTED
assert preserved() == before, 'Private backend credential or workspace changed'
adb('shell', 'am', 'start', '-n', PACKAGE + '/io.github.gplaider.tinyagent.AppActivity')
report = dict(serial='EDGE40_ROOT_SERIAL', previous_apk_sha256=old_hash, phone_apk_sha256=EXPECTED,
              install=result, backend_credential_preserved=True, workspace_source_preserved=True)
(ROOT / 'evidence/edge40-v12-phone-update.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report))

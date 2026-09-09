"""Read-only Pacman proof after real UI preparation and PackageInstaller confirmation."""
from pathlib import Path
import subprocess
import json
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ADB = Path.home() / 'AppData/Local/Android/Sdk/platform-tools/adb.exe'
SERIAL = '000501423003390'
PACKAGE = 'io.github.gplaider.tinyagent.debug'

def adb(*args):
    return subprocess.check_output([str(ADB), '-s', SERIAL, *args], timeout=30).decode().strip()

def prefs(name):
    raw = adb('shell', 'run-as', PACKAGE, 'cat', 'shared_prefs/' + name + '.xml')
    return {n.get('name'): n.get('value', n.text) for n in ET.fromstring(raw)}

assert adb('shell', 'getprop', 'ro.serialno') == SERIAL
assert adb('shell', 'id').startswith('uid=2000(')
assert adb('shell', 'getenforce') == 'Enforcing'
stored = adb('shell', 'run-as', PACKAGE, 'ls', 'shared_prefs').splitlines()
assert 'connection.xml' not in stored or prefs('connection').get('rootAllowed', 'false') == 'false'
processes = adb('shell', 'ps', '-A', '-o', 'UID,PID,PPID,NAME').splitlines()
app = next(line.split() for line in processes if line.endswith(' ' + PACKAGE))
assert int(app[0]) >= 10000
proot = next(line.split() for line in processes if line.split()[-1] == 'libproot.so' and line.split()[2] == app[1])
backend = next(line.split() for line in processes if line.split()[-1] == 'opencode' and line.split()[2] == proot[1])
assert backend[0] == proot[0] == app[0]
log = adb('shell', 'run-as', PACKAGE, 'cat', 'files/linux/backend.log')
assert 'opencode server listening on http://127.0.0.1:4097' in log
install = prefs('installer')
assert install['package'] == 'io.github.gplaider.tinyagent.installfixture'
assert install['code'] == '0' and install['route'] == '0'
installed = adb('shell', 'pm', 'path', install['package']).removeprefix('package:')
assert installed.startswith('/data/app/')
apk = adb('shell', 'pm', 'path', PACKAGE).removeprefix('package:')
report = dict(serial=SERIAL, apk_sha256=adb('shell', 'sha256sum', apk).split()[0],
              android_uid=int(app[0]), processes=[app, proot, backend], root_allowed=False,
              runtime=prefs('runtime'), stock_install=install,
              fixture_sha256=adb('shell', 'sha256sum', installed).split()[0],
              limits='No clean-stock claim: unlocked custom-ROM test device. No provider response or phone APK self-build acceptance.')
(ROOT / 'evidence/stock-integration.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))

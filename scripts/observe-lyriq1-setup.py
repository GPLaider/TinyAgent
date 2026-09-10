"""Observe preparation already started through UI; no private-file/root access."""
import json
from pathlib import Path
import subprocess
import time
import sys
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ADB = Path.home() / 'AppData/Local/Android/Sdk/platform-tools/adb.exe'
TARGET = '100.79.134.53:5555'
device = sys.argv[2] if len(sys.argv) > 2 else 'lyriq1'
assert device in ('lyriq1', 'pacman')
if device == 'pacman': TARGET = '000501423003390'
hardware = 'ZY22J58799' if device == 'lyriq1' else TARGET
variant = sys.argv[3] if len(sys.argv) > 3 else 'debug'
assert variant in ('debug', 'release')
PACKAGE = 'io.github.gplaider.tinyagent' + ('.debug' if variant == 'debug' else '')
version = sys.argv[1] if len(sys.argv) > 1 else 'v16'
assert re.fullmatch(r'v\d+', version)
def adb(*args):
    return subprocess.check_output([str(ADB), '-s', TARGET, *args], timeout=40).decode()

assert adb('shell', 'getprop', 'ro.serialno').strip() == hardware
assert adb('shell', 'getenforce').strip() == 'Enforcing'
deadline = time.monotonic() + 600
last = None
while time.monotonic() < deadline:
    try:
        dumped = adb('shell', 'uiautomator', 'dump', '/data/local/tmp/tinyagent-current-ui.xml')
    except subprocess.CalledProcessError as error:
        if error.returncode != 137:
            raise
        print('UI observer was killed (137); retrying observation, not preparation', flush=True)
        time.sleep(10)
        continue
    if 'UI hierchary dumped to:' not in dumped:
        print('UI still changing; waiting for a fresh snapshot', flush=True)
        time.sleep(10)
        continue
    xml = adb('shell', 'cat', '/data/local/tmp/tinyagent-current-ui.xml')
    texts = [n.get('text', '') for n in ET.fromstring(xml).iter('node')]
    status = next((t for t in texts if t.startswith(('환경 준비 실패', '환경 준비 완료', 'Fedora 설치 완료.'))), None)
    if texts != last:
        print(json.dumps(texts, ensure_ascii=False), flush=True)
        last = texts
    if status:
        rows = [r.split() for r in adb('shell', 'ps', '-A', '-o', 'UID,PID,PPID,NAME').splitlines()[1:]]
        app = next(r for r in rows if r[3] == PACKAGE)
        processes = [r for r in rows if r[0] == app[0]]
        apk = adb('shell', 'pm', 'path', PACKAGE).strip().removeprefix('package:')
        report = dict(serial=hardware, package=PACKAGE, status=status, app_uid=int(app[0]), processes=processes,
                      apk_sha256=adb('shell', 'sha256sum', apk).split()[0],
                      fingerprint=adb('shell', 'getprop', 'ro.build.fingerprint').strip(),
                      scope='UI preparation and app-UID process observation; no app ADB pairing or root')
        suffix = '-release' if variant == 'release' else ''
        (ROOT/f'evidence/{device}-{version}{suffix}-ui-setup.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        assert status.startswith(('환경 준비 완료', 'Fedora 설치 완료.')), status
        assert int(app[0]) >= 10000
        assert {'libproot.so', 'opencode'} <= {r[3] for r in processes}
        print('PASS: UI ready and app-UID PRoot/OpenCode processes', flush=True)
        break
    time.sleep(10)
else:
    raise AssertionError('Preparation status not reached within 600 seconds')

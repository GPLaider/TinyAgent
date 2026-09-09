"""A second selected APK must not replace an Android approval-pending session."""
import json
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ADB = Path.home() / 'AppData/Local/Android/Sdk/platform-tools/adb.exe'
SERIAL = '000501423003390'
PACKAGE = 'io.github.gplaider.tinyagent.debug'

def adb(*args):
    return subprocess.check_output([str(ADB), '-s', SERIAL, *args], timeout=30).decode().strip()

def tap(label):
    subprocess.run([sys.executable, '-I', '-S', '-X', 'utf8', str(ROOT / 'scripts/device-ui.py'), SERIAL, '--tap', label], check=True, timeout=30)

def state():
    return {n.get('name'): n.get('value', n.text) for n in ET.fromstring(adb('shell', 'run-as', PACKAGE, 'cat', 'shared_prefs/installer.xml'))}

assert adb('shell', 'getprop', 'ro.serialno') == SERIAL
assert state()['route'] == '0', 'Open the installer on Stock after its fixture test'
assert not state().get('confirmation'), 'Finish the prior approval before starting this test'
tap('파일에서 APK 선택')
tap('tinyagent-install-check.apk')
for _ in range(30):
    first = state()
    if first.get('confirmation'): break
    time.sleep(1)
else: raise AssertionError('No Android confirmation received')
tap('파일에서 APK 선택')
tap('tinyagent-install-check.apk')
for _ in range(30):
    second = state()
    if '기존 Android 설치 결과' in second['status']: break
    time.sleep(1)
assert first['session'] == second['session']
assert second['confirmation'] == first['confirmation']
assert '기존 Android 설치 결과' in second['status']
tap('ANDROID 승인 화면 열기')
tap('Update')
for _ in range(30):
    final = state()
    if final.get('code') == '0': break
    time.sleep(1)
else: raise AssertionError('Original pending install did not complete')
apk = adb('shell', 'pm', 'path', PACKAGE).removeprefix('package:')
report = dict(serial=SERIAL, apk_sha256=adb('shell', 'sha256sum', apk).split()[0],
              session=first['session'], duplicate_rejected=True, original_completed=final['code'] == '0')
(ROOT / 'evidence/install-pending-guard.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
print('Pending session preserved; original installation completed')

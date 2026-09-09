"""Three in-app fixture installs on one explicitly selected route. Installer UI must be open."""
import argparse
import json
import re
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('serial', choices=['000501423003390', '100.79.65.42:5555'])
parser.add_argument('route', choices=['stock', 'developer', 'root'])
args = parser.parse_args()
ADB = Path.home() / 'AppData/Local/Android/Sdk/platform-tools/adb.exe'
PACKAGE = 'io.github.gplaider.tinyagent.debug'
FIXTURE = 'io.github.gplaider.tinyagent.installfixture'
labels = ['Stock · Android 승인', 'Developer · self-ADB', 'Root · self root-ADB']
route = ['stock', 'developer', 'root'].index(args.route)
def adb(*command):
    return subprocess.check_output([str(ADB), '-s', args.serial, *command], timeout=45).decode().strip()
def tree():
    adb('shell', 'uiautomator', 'dump', '/sdcard/tinyagent-install-check.xml')
    return ET.fromstring(adb('shell', 'cat', '/sdcard/tinyagent-install-check.xml'))
def tap(label):
    nodes = tree()
    node = next(n for n in nodes.iter('node') if label in (n.get('text'), n.get('content-desc')))
    x1,y1,x2,y2 = map(int, re.findall(r'\d+', node.get('bounds')))
    assert x2>x1 and y2>y1
    adb('shell', 'input', 'tap', str((x1+x2)//2), str((y1+y2)//2))
def state():
    if 'installer.xml' not in adb('shell', 'run-as', PACKAGE, 'ls', 'shared_prefs').splitlines(): return {}
    raw = adb('shell', 'run-as', PACKAGE, 'cat', 'shared_prefs/installer.xml')
    return {n.get('name'): n.get('value', n.text) for n in ET.fromstring(raw)}

expected_serial = '000501423003390' if args.serial == '000501423003390' else 'ZY22HZPLL8'
assert adb('shell', 'getprop', 'ro.serialno') == expected_serial
nodes = tree()
current = next(n.get('text') for n in nodes.iter('node') if n.get('text') in labels)
if current != labels[route]: tap(current); tap(labels[route])
results = []
for iteration in range(3):
    before = state().get('updated', '')
    tap('파일에서 APK 선택')
    tap('tinyagent-install-check.apk')
    deadline = time.monotonic()+90
    while time.monotonic()<deadline:
        result = state()
        if result.get('updated', '') != before and int(result.get('route', -1)) == route:
            if result.get('confirmation'):
                tap('ANDROID 승인 화면 열기')
                confirmation = tree()
                assert any(n.get('text') == 'TinyAgent Install Check' for n in confirmation.iter('node'))
                choices = {n.get('text') for n in confirmation.iter('node')}
                tap(next(label for label in ['Update', 'Install', '업데이트', '설치'] if label in choices))
            elif result.get('code') == '0': break
            elif result.get('code') == '1': raise AssertionError(result['status'])
        time.sleep(1)
    else: raise AssertionError('Install result timeout: '+str(result))
    installed = adb('shell', 'pm', 'path', FIXTURE).removeprefix('package:')
    assert installed.startswith('/data/app/')
    results.append(dict(iteration=iteration+1, result=result, installed_sha256=adb('shell', 'sha256sum', installed).split()[0]))
    print(args.route, iteration+1, 'passed', flush=True)
apk = adb('shell', 'pm', 'path', PACKAGE).removeprefix('package:')
report = dict(serial=expected_serial, route=args.route, apk_sha256=adb('shell', 'sha256sum', apk).split()[0], results=results,
              scope='In-app fixture installation only; no self-build or complete release acceptance')
(ROOT / ('evidence/install-'+args.route+'-'+expected_serial+'.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

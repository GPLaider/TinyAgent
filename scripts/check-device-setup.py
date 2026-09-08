"""Press the real setup button and record the app-owned installer result."""
import argparse
import hashlib
import json
import re
import runpy
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ui = runpy.run_path(str(ROOT / 'scripts/check-device-adb.py'))
adb, snapshot, tap = ui['adb'], ui['snapshot'], ui['tap']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', required=True)
    args = parser.parse_args()
    assert re.fullmatch('[a-z0-9-]+', args.name)
    assert adb('shell', 'getprop', 'ro.serialno').decode().strip() == ui['SERIAL']
    out = ROOT / 'evidence' / args.name
    out.mkdir(exist_ok=False)
    adb('shell', 'input', 'keyevent', '224')
    assert 'deviceLocked=0' in adb('shell', 'dumpsys', 'trust').decode()
    adb('shell', 'wm', 'dismiss-keyguard')
    adb('shell', 'am', 'force-stop', ui['PACKAGE'])
    adb('shell', 'am', 'start', '-W', '-n', ui['PACKAGE'] + '/io.github.gplaider.tinyagent.AppActivity')
    before = snapshot()
    (out / 'before.xml').write_bytes(before)
    tree = ET.fromstring(before)
    switch = next(n for n in tree.iter('node') if n.get('text') == 'Unrestricted root 연결 허용')
    if switch.get('checked') != 'true':
        tap(switch)
    for attempt in range(7):
        tree = ET.fromstring(snapshot())
        buttons = [n for n in tree.iter('node') if n.get('text', '').lower() == 'fedora 환경 준비']
        if buttons:
            tap(buttons[0])
            break
        adb('shell', 'input', 'swipe', '540', '1900', '540', '700', '350')
    else:
        raise AssertionError('Setup button not found')
    time.sleep(1)
    tree = ET.fromstring(snapshot())
    for node in tree.iter('node'):
        if node.get('resource-id') == 'com.android.permissioncontroller:id/permission_allow_button':
            tap(node)
            break
    statuses = []
    status = ''
    for attempt in range(45):
        # This preference stores only public setup progress, not credentials.
        raw = adb('shell', 'cat', '/data/user/0/' + ui['PACKAGE'] + '/shared_prefs/runtime.xml')
        status = ET.fromstring(raw).find("string[@name='status']").text or ''
        if not statuses or statuses[-1] != status:
            statuses.append(status)
            print(status, flush=True)
        if '설치 완료.' in status or '환경 준비 실패:' in status:
            break
        time.sleep(2)
    adb('shell', 'input', 'keyevent', '224')
    adb('shell', 'wm', 'dismiss-keyguard')
    (out / 'after.xml').write_bytes(snapshot())
    (out / 'screen.png').write_bytes(adb('exec-out', 'screencap', '-p'))
    path = adb('shell', 'pm', 'path', ui['PACKAGE']).decode().strip().removeprefix('package:')
    apk = adb('shell', 'sha256sum', path).decode().split()[0]
    report = dict(serial=ui['SERIAL'], apk_sha256=apk, passed='설치 완료.' in status,
                  statuses=statuses, files={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir()})
    (out / 'result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    assert report['passed'], status


if __name__ == '__main__':
    main()

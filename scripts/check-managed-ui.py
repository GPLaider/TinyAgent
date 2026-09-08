"""Verify native authentication opens the actual embedded OpenCode GUI."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ui = runpy.run_path(str(ROOT / 'scripts/check-device-adb.py'))
adb, snapshot, tap = ui['adb'], ui['snapshot'], ui['tap']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', required=True)
    args = parser.parse_args()
    assert args.name.replace('-', '').isalnum()
    assert adb('shell', 'getprop', 'ro.serialno').decode().strip() == ui['SERIAL']
    out = ROOT / 'evidence' / args.name
    out.mkdir(exist_ok=False)
    adb('shell', 'input', 'keyevent', '224')
    assert 'deviceLocked=0' in adb('shell', 'dumpsys', 'trust').decode()
    adb('shell', 'wm', 'dismiss-keyguard')
    adb('shell', 'am', 'force-stop', ui['PACKAGE'])
    adb('shell', 'am', 'start', '-W', '-n', ui['PACKAGE'] + '/io.github.gplaider.tinyagent.AppActivity')
    tree = ET.fromstring(snapshot())
    tap(next(n for n in tree.iter('node') if n.get('text') == '이 기기 연결 확인'))
    for attempt in range(8):
        time.sleep(1)
        tree = ET.fromstring(snapshot())
        if any('앱 비공개 파일 일치' in n.get('text', '') for n in tree.iter('node')):
            break
    else:
        raise AssertionError('Self verification did not complete')
    for attempt in range(8):
        buttons = [n for n in tree.iter('node') if n.get('text', '').lower() == '로컬 opencode 열기']
        if buttons:
            tap(buttons[0])
            break
        adb('shell', 'input', 'swipe', '540', '1900', '540', '700', '350')
        tree = ET.fromstring(snapshot())
    else:
        raise AssertionError('Open button not found')
    passed = False
    for attempt in range(8):
        time.sleep(2)
        final = snapshot()
        tree = ET.fromstring(final)
        texts = '\n'.join(n.get('text', '') for n in tree.iter('node'))
        passed = any(n.get('class') == 'android.webkit.WebView' for n in tree.iter('node'))
        passed = passed and ('프로젝트' in texts) and ('백엔드 암호' not in texts)
        if passed:
            break
    (out / 'screen.xml').write_bytes(final)
    (out / 'screen.png').write_bytes(adb('exec-out', 'screencap', '-p'))
    path = adb('shell', 'pm', 'path', ui['PACKAGE']).decode().strip().removeprefix('package:')
    report = dict(serial=ui['SERIAL'], passed=passed,
                  apk_sha256=adb('shell', 'sha256sum', path).decode().split()[0],
                  files={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir()})
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(texts)
    assert passed, 'Managed GUI/auth acceptance failed'


if __name__ == '__main__':
    main()

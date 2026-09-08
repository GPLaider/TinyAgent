"""Real-device layout, disclosure, keyboard/back and one-tap backend acceptance."""
import argparse
import hashlib
import json
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
    assert args.name.replace('-', '').isalnum()
    assert adb('shell', 'getprop', 'ro.serialno').decode().strip() == ui['SERIAL']
    out = ROOT / 'evidence' / args.name
    out.mkdir(exist_ok=False)
    adb('shell', 'input', 'keyevent', '224')
    assert 'deviceLocked=0' in adb('shell', 'dumpsys', 'trust').decode()
    adb('shell', 'wm', 'dismiss-keyguard')
    adb('shell', 'am', 'force-stop', ui['PACKAGE'])
    adb('shell', 'am', 'start', '-W', '-n', ui['PACKAGE'] + '/io.github.gplaider.tinyagent.AppActivity')

    def capture(name):
        raw = snapshot()
        (out / (name + '.xml')).write_bytes(raw)
        (out / (name + '.png')).write_bytes(adb('exec-out', 'screencap', '-p'))
        return ET.fromstring(raw)

    def find(tree, label):
        return next(n for n in tree.iter('node')
                    if n.get('text') == label or n.get('content-desc') == label)

    tree = capture('setup')
    assert not any(n.get('class') == 'android.widget.EditText' for n in tree.iter('node'))
    assert find(tree, '대화 시작하기').get('enabled') == 'true'
    assert find(tree, 'Root 실행 허용').get('checked') == 'true', 'Test requires previously granted root'
    tap(find(tree, '고급 연결 설정'))
    tree = capture('advanced')
    port = next(n for n in tree.iter('node') if n.get('class') == 'android.widget.EditText')
    assert port.get('text') == '5555'
    tap(port)
    tree = capture('keyboard')
    adb('shell', 'input', 'keyevent', '4')
    tree = capture('keyboard-dismissed')
    assert find(tree, '작업 환경') is not None
    tap(find(tree, '고급 연결 설정'))
    tree = ET.fromstring(snapshot())
    tap(find(tree, '대화 시작하기'))
    for _ in range(12):
        time.sleep(2)
        tree = ET.fromstring(snapshot())
        if any(n.get('class') == 'android.webkit.WebView' for n in tree.iter('node')):
            if any('프로젝트' in n.get('text', '') for n in tree.iter('node')):
                break
    else:
        capture('failed-open')
        raise AssertionError('One-tap authenticated GUI failed')
    capture('conversation-home')
    apk = adb('shell', 'pm', 'path', ui['PACKAGE']).decode().strip().removeprefix('package:')
    report = dict(serial=ui['SERIAL'], passed=True,
                  apk_sha256=adb('shell', 'sha256sum', apk).decode().split()[0],
                  checks=['collapsed diagnostics', 'advanced port preserved', 'keyboard Back stays in app',
                          'one-tap self verification and authenticated GUI'],
                  files={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir()})
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()

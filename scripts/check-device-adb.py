"""Exercise installed TinyAgent's real setup UI on the explicitly selected phone."""
import argparse
import hashlib
import json
import re
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ADB = Path.home() / 'AppData/Local/Android/Sdk/platform-tools/adb.exe'
TARGET = '100.79.65.42:5555'
SERIAL = 'ZY22HZPLL8'
PACKAGE = 'io.github.gplaider.tinyagent.debug'
ROOT = Path(__file__).resolve().parents[1]

def select_device(target):
    global TARGET, SERIAL
    SERIAL = {'100.79.65.42:5555': 'ZY22HZPLL8', '100.79.134.53:5555': 'ZY22J58799', '000501423003390': '000501423003390'}[target]
    TARGET = target
    return SERIAL


def adb(*args):
    return subprocess.run([str(ADB), '-s', TARGET, *args], check=True,
                          capture_output=True, timeout=35).stdout


def snapshot():
    adb('shell', 'uiautomator', 'dump', '/data/local/tmp/tinyagent-ui.xml')
    return adb('shell', 'cat', '/data/local/tmp/tinyagent-ui.xml')


def tap(node):
    assert node.get('enabled') == 'true', 'UI control is disabled'
    x1, y1, x2, y2 = map(int, re.findall(r'\d+', node.get('bounds')))
    adb('shell', 'input', 'tap', str((x1+x2)//2), str((y1+y2)//2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', required=True)
    parser.add_argument('--readonly', action='store_true')
    parser.add_argument('--backend-unavailable', action='store_true')
    args = parser.parse_args()
    assert re.fullmatch(r'[a-z0-9-]+', args.name)
    assert adb('shell', 'getprop', 'ro.serialno').decode().strip() == SERIAL
    destination = ROOT / 'evidence' / args.name
    destination.mkdir(exist_ok=False)
    adb('shell', 'input', 'keyevent', '224')
    assert 'deviceLocked=0' in adb('shell', 'dumpsys', 'trust').decode(), 'Owner unlock required'
    adb('shell', 'wm', 'dismiss-keyguard')
    time.sleep(1)
    adb('shell', 'am', 'start', '-W', '-n', PACKAGE + '/io.github.gplaider.tinyagent.AppActivity')
    before = snapshot()
    (destination / 'before.xml').write_bytes(before)
    tree = ET.fromstring(before)
    switch = next(n for n in tree.iter('node') if n.get('text') == 'Unrestricted root 연결 허용')
    if (switch.get('checked') == 'true') == args.readonly:
        tap(switch)
    button = next(n for n in tree.iter('node') if n.get('text') == '이 기기 연결 확인')
    tap(button)
    for _ in range(6):
        time.sleep(1)
        after = snapshot()
        tree = ET.fromstring(after)
        if not any(n.get('text') == '연결 확인 중단' for n in tree.iter('node')):
            break
    texts = '\n'.join(n.get('text', '') for n in tree.iter('node'))
    expected = '읽기 전용 조회 완료' if args.readonly else '앱 비공개 파일 일치: 자기 Android 확인. 실행 UID=0.'
    passed = expected in texts
    if args.backend_unavailable and passed:
        for _ in range(5):
            buttons = [n for n in tree.iter('node') if n.get('text') == '로컬 OPENCODE 열기']
            if buttons:
                tap(buttons[0])
                break
            scroll = next(n for n in tree.iter('node') if n.get('class') == 'android.widget.ScrollView')
            x1, y1, x2, y2 = map(int, re.findall(r'\d+', scroll.get('bounds')))
            adb('shell', 'input', 'swipe', str((x1+x2)//2), str(y2-150),
                str((x1+x2)//2), str(y1+150), '300')
            tree = ET.fromstring(snapshot())
        time.sleep(2)
        after = snapshot()
        texts = '\n'.join(n.get('text', '') for n in ET.fromstring(after).iter('node'))
        passed = '로컬 백엔드 확인 실패:' in texts
    (destination / 'after.xml').write_bytes(after)
    (destination / 'screen.png').write_bytes(adb('exec-out', 'screencap', '-p'))
    (destination / 'transcript.txt').write_text(texts, encoding='utf-8')
    apk_path = adb('shell', 'pm', 'path', PACKAGE).decode().strip().removeprefix('package:')
    apk_hash = adb('shell', 'sha256sum', apk_path).decode().split()[0]
    report = dict(device=SERIAL, transport=TARGET, apk_sha256=apk_hash,
                  passed=passed, readonly=args.readonly, backend_unavailable=args.backend_unavailable,
                  files={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in destination.iterdir() if p.is_file()})
    (destination / 'result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    print(texts)
    if not passed:
        raise SystemExit(1)


if __name__ == '__main__':
    main()

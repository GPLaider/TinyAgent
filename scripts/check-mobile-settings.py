"""Exercise packaged OpenCode settings and Android Back on the actual phone."""
import argparse
import json
from pathlib import Path
import runpy
import re
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ui = runpy.run_path(str(ROOT / 'scripts/check-device-adb.py'))
adb, snapshot, tap = ui['adb'], ui['snapshot'], ui['tap']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', required=True)
    parser.add_argument('--expect-back-failure', action='store_true')
    parser.add_argument('--provider-form', action='store_true')
    parser.add_argument('--serial', choices=['100.79.65.42:5555', '000501423003390'], default='100.79.65.42:5555')
    args = parser.parse_args()
    ui['SERIAL'] = ui['select_device'](args.serial)
    assert args.name.replace('-', '').isalnum()
    assert adb('shell', 'getprop', 'ro.serialno').decode().strip() == ui['SERIAL']
    out = ROOT / 'evidence' / args.name
    out.mkdir(exist_ok=False)
    adb('shell', 'input', 'keyevent', '224')
    assert 'deviceLocked=0' in adb('shell', 'dumpsys', 'trust').decode()
    adb('shell', 'wm', 'dismiss-keyguard')
    adb('shell', 'am', 'force-stop', ui['PACKAGE'])
    adb('shell', 'am', 'start', '-W', '-n', ui['PACKAGE'] + '/io.github.gplaider.tinyagent.AppActivity')

    def tree():
        return ET.fromstring(snapshot())

    def texts(nodes):
        return '\n'.join(n.get('text', '') for n in nodes.iter('node'))

    def find(nodes, label):
        web = next((n for n in nodes.iter('node') if n.get('class') == 'android.webkit.WebView'), None)
        limit = list(map(int, re.findall(r'\d+', web.get('bounds')))) if web is not None else None
        for n in nodes.iter('node'):
            if n.get('text') not in (label, label + ' ›') and n.get('content-desc') != label:
                continue
            bounds = list(map(int, re.findall(r'\d+', n.get('bounds'))))
            if limit and not (limit[0] <= bounds[0] < bounds[2] <= limit[2]
                              and limit[1] <= bounds[1] < bounds[3] <= limit[3]):
                continue
            return n
        return None

    def capture(name):
        raw = snapshot()
        (out / (name + '.xml')).write_bytes(raw)
        (out / (name + '.png')).write_bytes(adb('exec-out', 'screencap', '-p'))
        return ET.fromstring(raw)

    tap(find(tree(), '대화 시작하기'))
    for _ in range(15):
        nodes = tree()
        if any(n.get('class') == 'android.webkit.WebView' for n in nodes.iter('node')) and '프로젝트' in texts(nodes):
            break
        time.sleep(2)
    else:
        capture('failed-home')
        raise AssertionError('Packaged GUI did not expose Settings')
    for _ in range(6):
        if find(nodes, '설정') is not None:
            break
        web = next(n for n in nodes.iter('node') if n.get('class') == 'android.webkit.WebView')
        x1, y1, x2, y2 = map(int, re.findall(r'\d+', web.get('bounds')))
        adb('shell', 'input', 'swipe', str((x1+x2)//2), str(y2-100), str((x1+x2)//2), str(y1+100), '300')
        nodes = tree()
    capture('home-before-settings')
    assert find(nodes, '설정') is not None, 'Settings not reachable in WebView viewport'
    tap(find(nodes, '설정'))
    nodes = capture('menu')
    assert find(nodes, '단축키') is None, 'Desktop keyboard shortcuts are exposed on the phone'
    tap(find(nodes, '일반'))
    nodes = capture('general')
    assert '터미널 셸' in texts(nodes)
    adb('shell', 'input', 'keyevent', '4')
    nodes = capture('android-back')
    passed = find(nodes, '공급자') is not None and find(nodes, '모델') is not None
    if not args.expect_back_failure:
        assert passed, 'Android Back skipped settings menu'
        for label in ['공급자', '모델', '서버']:
            tap(find(nodes, label))
            capture(label)
            adb('shell', 'input', 'keyevent', '4')
            nodes = tree()
            assert find(nodes, '일반') is not None, label
        if args.provider_form:
            tap(find(nodes, '공급자'))
            for _ in range(12):
                nodes = tree()
                custom = find(nodes, '사용자 지정 공급자')
                if custom is not None:
                    items = list(nodes.iter('node'))
                    buttons = [n for n in items[items.index(custom)+1:]
                               if n.get('class') == 'android.widget.Button'
                               and '연결' in n.get('text', '')]
                    if buttons:
                        tap(buttons[0])
                        break
                adb('shell', 'input', 'swipe', '540', '2040', '540', '700', '300')
            else:
                capture('custom-unreachable')
                raise AssertionError('Custom provider action is unreachable')
            nodes = capture('custom-form')
            assert '공급자 ID' in texts(nodes)
            field = next(n for n in nodes.iter('node') if n.get('class') == 'android.widget.EditText'
                         and n.get('hint', '').endswith('소문자, 숫자, 하이픈 또는 밑줄'))
            tap(field)
            nodes = tree()
            assert any(n.get('focused') == 'true' and n.get('resource-id') == field.get('resource-id')
                       for n in nodes.iter('node')), 'Provider ID input did not receive focus'
            adb('shell', 'input', 'text', 'tinyagent-ui-check')
            capture('custom-keyboard')
            adb('shell', 'input', 'keyevent', '4')
            nodes = capture('custom-keyboard-dismissed')
            assert 'tinyagent-ui-check' in texts(nodes), 'Keyboard Back closed the provider form'
            adb('shell', 'input', 'keyevent', '4')
            nodes = tree()
            assert '연결된 공급자' in texts(nodes), 'Provider Back did not restore providers'
            adb('shell', 'input', 'keyevent', '4')
            nodes = tree()
            assert find(nodes, '일반') is not None
        adb('shell', 'input', 'keyevent', '4')
        nodes = capture('closed')
        assert find(nodes, '프로젝트') is not None
    apk = adb('shell', 'pm', 'path', ui['PACKAGE']).decode().strip().removeprefix('package:')
    report = dict(serial=ui['SERIAL'], back_passed=passed, expected_failure=args.expect_back_failure,
                  provider_form_checked=args.provider_form,
                  apk_sha256=adb('shell', 'sha256sum', apk).decode().split()[0])
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    if args.expect_back_failure:
        assert not passed, 'Expected old APK to reproduce Back failure'


if __name__ == '__main__':
    main()

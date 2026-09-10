"""Stop through the native button, then verify the recorded backend PID disappeared."""
import argparse
import hashlib
import json
from pathlib import Path
import re
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
    assert re.fullmatch('[a-z0-9-]+', args.name)
    assert adb('shell', 'getprop', 'ro.serialno').decode().strip() == ui['SERIAL']
    out = ROOT / 'evidence' / args.name
    out.mkdir(exist_ok=False)
    pid = adb('shell', 'cat', '/data/local/tinyagent/run/backend.state').decode().split()[0]
    assert pid.isdecimal()
    assert adb('shell', 'readlink', '/proc/' + pid + '/root').decode().strip() == '/data/local/tinyagent/runtime/0.1.2/rootfs'
    adb('shell', 'input', 'keyevent', '224')
    assert 'deviceLocked=0' in adb('shell', 'dumpsys', 'trust').decode()
    adb('shell', 'wm', 'dismiss-keyguard')
    adb('shell', 'am', 'force-stop', ui['PACKAGE'])
    adb('shell', 'am', 'start', '-W', '-n', ui['PACKAGE'] + '/io.github.gplaider.tinyagent.AppActivity')
    for attempt in range(8):
        tree = ET.fromstring(snapshot())
        buttons = [n for n in tree.iter('node') if n.get('text') == '로컬 백엔드 중단']
        if buttons:
            tap(buttons[0])
            break
        adb('shell', 'input', 'swipe', '540', '1900', '540', '700', '350')
    else:
        raise AssertionError('Stop button not found')
    status = ''
    for attempt in range(15):
        time.sleep(1)
        raw = adb('shell', 'cat', '/data/user/0/' + ui['PACKAGE'] + '/shared_prefs/runtime.xml')
        status = ET.fromstring(raw).find("string[@name='status']").text or ''
        if '로컬 백엔드를 중단했습니다.' in status:
            break
    assert '로컬 백엔드를 중단했습니다.' in status, status
    adb('shell', 'test', '!', '-d', '/proc/' + pid)
    marker = adb('exec-out', 'cat', '/data/local/tinyagent/workspaces/setup-preservation-marker.txt')
    assert marker == (ROOT / 'evidence/setup-preservation-marker.txt').read_bytes()
    (out / 'screen.xml').write_bytes(snapshot())
    (out / 'screen.png').write_bytes(adb('exec-out', 'screencap', '-p'))
    report = dict(serial=ui['SERIAL'], stopped_pid=pid, passed=True, status=status,
                  marker_sha256=hashlib.sha256(marker).hexdigest())
    (out / 'result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

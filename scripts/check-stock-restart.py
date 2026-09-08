"""Three real UI runtime start/stop cycles, then force-stop/reopen recovery on Pacman."""
from pathlib import Path
import subprocess
import time
import re
import json
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ADB = Path.home() / 'AppData/Local/Android/Sdk/platform-tools/adb.exe'
SERIAL = 'USB_TEST_SERIAL'
PACKAGE = 'io.github.gplaider.tinyagent.debug'
def adb(*args):
    return subprocess.check_output([str(ADB), '-s', SERIAL, *args], timeout=30).decode().strip()
def tap(label):
    adb('shell', 'uiautomator', 'dump', '/sdcard/tinyagent-runtime-check.xml')
    tree = ET.fromstring(adb('shell', 'cat', '/sdcard/tinyagent-runtime-check.xml'))
    node = next(n for n in tree.iter('node') if n.get('text') == label or n.get('content-desc') == label)
    x1, y1, x2, y2 = map(int, re.findall(r'\d+', node.get('bounds')))
    assert x2 > x1 and y2 > y1
    adb('shell', 'input', 'tap', str((x1+x2)//2), str((y1+y2)//2))
def runtime_status():
    tree = ET.fromstring(adb('shell', 'run-as', PACKAGE, 'cat', 'shared_prefs/runtime.xml'))
    return next(n.text for n in tree if n.get('name') == 'status')
def processes():
    rows = [line.split() for line in adb('shell', 'ps', '-A', '-o', 'UID,PID,PPID,NAME').splitlines()[1:]]
    app = next(row for row in rows if row[3] == PACKAGE)
    return [row for row in rows if row[0] == app[0] and row[3] in ('opencode', 'libproot.so')]
def wait_status(prefix):
    deadline = time.monotonic() + 75
    while time.monotonic() < deadline:
        value = runtime_status()
        if value.startswith(prefix): return value
        if value.startswith('환경 준비 실패'): raise AssertionError(value)
        time.sleep(1)
    raise AssertionError('runtime timeout: ' + value)

assert adb('shell', 'getprop', 'ro.serialno') == SERIAL
assert adb('shell', 'id').startswith('uid=2000(')
assert 'deviceLocked=0' in adb('shell', 'dumpsys', 'trust')
adb('shell', 'input', 'keyevent', '224')
adb('shell', 'wm', 'dismiss-keyguard')
adb('shell', 'am', 'force-stop', PACKAGE)
adb('shell', 'am', 'start', '-n', PACKAGE + '/io.github.gplaider.tinyagent.AppActivity')
results = []
for iteration in range(3):
    tap('Fedora 환경 준비')
    # A prior ready preference is not proof of a newly running process.
    time.sleep(2)
    wait_status('Fedora 설치 완료')
    running = processes()
    assert len(running) == 2 and all(int(row[0]) >= 10000 for row in running), running
    tap('진단 정보')
    tap('로컬 백엔드 중단')
    wait_status('로컬 백엔드를 중단')
    time.sleep(1)
    assert not processes(), 'Linux child survived stop'
    tap('진단 정보')
    results.append(dict(iteration=iteration+1, started=running, stopped=True))
    print('cycle', iteration+1, 'passed', flush=True)
tap('Fedora 환경 준비')
time.sleep(2)
wait_status('Fedora 설치 완료')
adb('shell', 'am', 'force-stop', PACKAGE)
adb('shell', 'am', 'start', '-n', PACKAGE + '/io.github.gplaider.tinyagent.AppActivity')
time.sleep(1)
# No Prepare tap: a previously running runtime must resume on application reopen.
time.sleep(2)
wait_status('Fedora 설치 완료')
assert len(processes()) == 2
apk = adb('shell', 'pm', 'path', PACKAGE).removeprefix('package:')
report = dict(serial=SERIAL, apk_sha256=adb('shell', 'sha256sum', apk).split()[0], cycles=results,
              force_stop_reopen=True, automatic_resume=True, scope='Runtime process lifecycle only; not the full release journeys')
(ROOT / 'evidence/stock-restart.json').write_text(json.dumps(report, indent=2)+'\n')
print('force-stop/reopen passed')

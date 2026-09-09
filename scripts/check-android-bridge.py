"""Actual Fedora-to-Android diagnostics plus rejection of another Android UID."""
import http.client
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
ADB = Path.home() / 'AppData/Local/Android/Sdk/platform-tools/adb.exe'
parser = argparse.ArgumentParser()
parser.add_argument('--serial', choices=['000501423003390', '100.79.65.42:5555'], default='000501423003390')
SERIAL = parser.parse_args().serial
EDGE = ':' in SERIAL
HARDWARE = 'ZY22HZPLL8' if EDGE else SERIAL
PORT = 14101 if EDGE else 14100
PACKAGE = 'io.github.gplaider.tinyagent.debug'

def adb(*args):
    return subprocess.check_output([str(ADB), '-s', SERIAL, *args], timeout=30).decode().strip()

assert adb('shell', 'getprop', 'ro.serialno') == HARDWARE
tool = adb('shell', 'run-as', PACKAGE, 'cat', 'files/linux/home/.tinyagent/ANDROID_TOOL.md')
socket = re.search(r'tinyagent-android-(\d+)-\d+', tool).group()
uid = int(socket.split('-')[2])

def inspect(mode, name):
    name = name + '-' + HARDWARE
    command = '/usr/bin/curl --fail-with-body --silent --show-error --max-time 90 --abstract-unix-socket ' + socket + ' http://localhost/inspect/' + mode
    subprocess.run([sys.executable, '-I', '-S', '-X', 'utf8', str(ROOT / 'scripts/probe-stock-backend.py'), '--serial', SERIAL, '--command', command, '--output', name], check=True, timeout=120)
    report = json.loads((ROOT / ('evidence/' + name + '.json')).read_text(encoding='utf-8'))
    output = next(part['state']['output'] for part in report['result']['parts'] if part.get('type') == 'tool')
    return json.JSONDecoder().raw_decode(output[output.index('{'):])[0]

stock = inspect('stock', 'android-bridge-stock')
assert stock['execution_uid'] == uid and stock['authority'] == 'app-sandbox'
developer = inspect('developer', 'android-bridge-developer')
if EDGE:
    assert 'UID=0' in developer['error'], 'Root adbd must not silently satisfy Developer mode'
    for iteration in range(3):
        root = inspect('root', 'android-bridge-root-' + str(iteration + 1))
        assert root['execution_uid'] == 0 and root['verified_self'] and root['root_selected']
else:
    assert developer['execution_uid'] == 2000 and developer['verified_self']
    denied = inspect('root', 'android-bridge-root-denied')
    assert denied['mode'] == 'root' and '허용되지' in denied['error']
adb('forward', 'tcp:' + str(PORT), 'localabstract:' + socket)
try:
    try:
        urllib.request.urlopen('http://127.0.0.1:' + str(PORT) + '/inspect/stock', timeout=5)
    except (http.client.RemoteDisconnected, ConnectionResetError):
        rejected = True
    else: raise AssertionError('ADB UID reached the app-only diagnostic socket')
finally:
    adb('forward', '--remove', 'tcp:' + str(PORT))
assert inspect('stock', 'android-bridge-after-foreign-uid')['execution_uid'] == uid
apk = adb('shell', 'pm', 'path', PACKAGE).removeprefix('package:')
result = dict(serial=HARDWARE, app_uid=uid, stock=True, developer=not EDGE, root_denied=not EDGE, root_iterations=3 if EDGE else 0, foreign_uid_rejected=rejected,
              apk_sha256=adb('shell', 'sha256sum', apk).split()[0], scope='Actual tool wiring; no model inference or arbitrary Android shell execution')
(ROOT / ('evidence/android-bridge-integration-' + HARDWARE + '.json')).write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
print('Android bridge: selected authority, mismatched authority rejection, foreign UID rejection and recovery passed on', HARDWARE)

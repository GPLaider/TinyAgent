"""Fixed Lyriq2 debug Activity test. ADB stages/observes, app UID executes dnfast."""
import argparse
import atexit
import hashlib
import json
import re
from pathlib import Path
import subprocess
import time

parser = argparse.ArgumentParser()
parser.add_argument('action', choices=['check', 'refresh', 'plan', 'install', 'recover', 'verify', 'network', 'cancel-preparation', 'timeout-process', 'result-contract'])
parser.add_argument('--candidate', default='b754437')
parser.add_argument('--apk', type=Path, default=Path('D:/TinyAgent-work/artifacts/tinyagent-dnfast-product-probe.apk'))
parser.add_argument('--keep-awake', action='store_true', help='ADB screen-awake control; not background acceptance')
parser.add_argument('--timeout-seconds', type=int, default=900, help='Explicit debug command deadline, 1..7200 seconds')
parser.add_argument('--overlay-sha256', default='291bbc1bda2e514d84ae93115c14c8289513243f07f70e3802d31e21f0cc8f55')
parser.add_argument('--manifest-sha256', default='d31a3c2b92f64f2836a4df3871af4b8ca84e74b648e481b9030bcb9f68c8e5e9')
args = parser.parse_args()
assert 1 <= args.timeout_seconds <= 7200
assert re.fullmatch('[0-9a-f]{7,40}', args.candidate)
assert all(re.fullmatch('[0-9a-f]{64}', value) for value in (args.overlay_sha256, args.manifest_sha256))
adb = Path.home() / 'AppData/Local/Android/Sdk/platform-tools/adb.exe'
serial = '100.79.65.42:5555'
package = 'io.github.gplaider.tinyagent.debug'

def call(*argv):
    return subprocess.check_output([str(adb), '-s', serial, *argv], timeout=60).decode()

assert call('shell', 'getprop', 'ro.serialno').strip() == 'ZY22HZPLL8'
stage = '/data/user/0/' + package + '/files/linux/shared/dnfast-product-' + args.candidate + '/'
assert call('shell', 'sha256sum', stage + 'root-overlay.tar.gz').split()[0] == args.overlay_sha256
assert call('shell', 'sha256sum', stage + 'manifest.json').split()[0] == args.manifest_sha256
apk = args.apk
apk_hash = hashlib.sha256(apk.read_bytes()).hexdigest()
installed = call('shell', 'pm', 'path', package).strip().removeprefix('package:')
assert call('shell', 'sha256sum', installed).split()[0] == apk_hash
call('shell', 'run-as', package, 'rm', '-f', 'files/dnfast-product-probe.log')
if args.keep_awake:
    previous_stay = call('shell', 'settings', 'get', 'global', 'stay_on_while_plugged_in').strip()
    assert previous_stay == 'null' or previous_stay.isdecimal(), previous_stay
    def restore_power():
        if previous_stay == 'null':
            call('shell', 'settings', 'delete', 'global', 'stay_on_while_plugged_in')
        else:
            call('shell', 'settings', 'put', 'global', 'stay_on_while_plugged_in', previous_stay)
    Path('evidence/dnfast-power-control-restore.json').write_text(json.dumps(
        {'serial': serial, 'hardware': 'ZY22HZPLL8', 'previous_stay_on_while_plugged_in': previous_stay}))
    atexit.register(restore_power)
    call('shell', 'svc', 'power', 'stayon', 'true')
    assert 'mWakefulness=Awake' in call('shell', 'dumpsys', 'power')
start = call('shell', 'am', 'start', '-W', '-f', '0x18000000', '-n',
             package + '/io.github.gplaider.tinyagent.DnfastProbeActivity', '--es', 'action', args.action,
             '--es', 'candidate', args.candidate, '--ei', 'timeout_seconds', str(args.timeout_seconds))
began = time.monotonic()
report = ''
while time.monotonic() - began < args.timeout_seconds + 200:
    try:
        report = call('exec-out', 'run-as', package, 'cat', 'files/dnfast-product-probe.log')
        if any(line.startswith(('PASS action=', 'FAIL:')) for line in report.splitlines()):
            break
    except subprocess.CalledProcessError:
        pass
    time.sleep(3)
result = {'serial': serial, 'hardware': 'ZY22HZPLL8', 'action': args.action, 'candidate': args.candidate,
          'command_timeout_seconds': args.timeout_seconds,
          'adb_screen_awake_control': args.keep_awake,
          'apk_sha256': apk_hash, 'launch': start, 'elapsed_seconds': time.monotonic() - began,
          'report': report, 'scope': 'Actual app Activity executes; ADB launch and evidence only'}
Path('evidence/dnfast-product-' + args.candidate + '-' + args.action + '.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(report)
assert 'PASS action=' + args.action in report, result

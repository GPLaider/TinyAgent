"""Run the debug app activity; ADB controls launch only, never executes the probe UID."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

parser = argparse.ArgumentParser()
parser.add_argument('mode', choices=['seed-direct', 'seed-loader', 'roundtrip'])
parser.add_argument('--apk', type=Path, default=Path('D:/TinyAgent-work/artifacts/tinyagent-fd-probe.apk'))
parser.add_argument('--anonymous', action='store_true')
args = parser.parse_args()
adb = Path.home() / 'AppData/Local/Android/Sdk/platform-tools/adb.exe'
serial = '100.79.65.42:5555'
package = 'io.github.gplaider.tinyagent.debug'
def call(*argv):
    return subprocess.check_output([str(adb), '-s', serial, *argv], timeout=60).decode()
assert call('shell', 'getprop', 'ro.serialno').strip() == 'ZY22HZPLL8'
# Remove only the stale, fixed probe report; retain all guest per-run evidence.
call('shell', 'run-as', package, 'rm', '-f', 'files/fd-roundtrip.log')
command = ['shell', 'am', 'start', '-W', '-f', '0x18000000', '-n', package + '/io.github.gplaider.tinyagent.FdRoundTripActivity']
if args.mode.startswith('seed-'):
    command += ['--ez', 'seed', 'true', '--ez', 'loader', str(args.mode == 'seed-loader').lower()]
    command += ['--ez', 'anonymous', str(args.anonymous).lower()]
start = call(*command)
report = ''
for _ in range(20):
    try:
        report = call('exec-out', 'run-as', package, 'cat', 'files/fd-roundtrip.log')
        if report.startswith(('PASS:', 'FAIL:', 'seed_exit=')):
            break
        time.sleep(2)
    except subprocess.CalledProcessError:
        time.sleep(2)
result = {'serial': serial, 'hardware': 'ZY22HZPLL8', 'mode': args.mode, 'launch': start,
          'report': report, 'scope': 'Actual app activity; run-as only reads the saved report'}
apk = args.apk
result['apk_sha256'] = hashlib.sha256(apk.read_bytes()).hexdigest()
Path('evidence/fd-' + args.mode + ('-anon' if args.anonymous else '') + '.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(report)
if args.mode == 'roundtrip':
    assert report.startswith('PASS:'), result
else:
    assert report.startswith('seed_exit=0\n') and '"phase":"complete"' in report, result

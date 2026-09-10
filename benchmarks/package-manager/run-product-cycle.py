"""Run the fixed phone reproduction, preserving each step before the next one."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys

parser = argparse.ArgumentParser()
parser.add_argument('--candidate', required=True)
parser.add_argument('--apk', type=Path, required=True)
parser.add_argument('--overlay-sha256', required=True)
parser.add_argument('--manifest-sha256', required=True)
parser.add_argument('--timeout-seconds', type=int, default=3600)
parser.add_argument('--keep-awake', action='store_true', help='Explicit awake control; not screen-off acceptance')
args = parser.parse_args()
assert re.fullmatch('[0-9a-f]{7,40}', args.candidate)
assert 1 <= args.timeout_seconds <= 7200
for value in (args.overlay_sha256, args.manifest_sha256):
    assert re.fullmatch('[0-9a-f]{64}', value)
root = Path(__file__).resolve().parents[2]
target = root / 'evidence' / ('dnfast-cycle-' + args.candidate + '-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
target.mkdir(exist_ok=False)
common = ['--candidate', args.candidate, '--apk', str(args.apk.resolve()),
          '--overlay-sha256', args.overlay_sha256, '--manifest-sha256', args.manifest_sha256,
          '--timeout-seconds', str(args.timeout_seconds)]
if args.keep_awake:
    common.append('--keep-awake')
adb = Path.home() / 'AppData/Local/Android/Sdk/platform-tools/adb.exe'
device_root = '/data/user/0/io.github.gplaider.tinyagent.debug/files/dnfast-product-' + args.candidate + '-v1/linux/rootfs'

def planning_state():
    def read(*command):
        run = subprocess.run([str(adb), '-s', '100.79.65.42:5555', 'shell', *command],
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
        return {'exit': run.returncode, 'output': run.stdout.decode(errors='replace')}
    hardware = read('getprop', 'ro.serialno')
    if hardware['exit'] or hardware['output'].strip() != 'ZY22HZPLL8':
        return {'skipped': 'Target hardware not verified'}
    identity = read('cat', device_root + '/.tinyagent-root-id')
    root_id = identity['output'].strip()
    if identity['exit'] or not re.fullmatch('[0-9a-f]{64}', root_id):
        return {'root_id': identity}
    directory = device_root + '/var/lib/dnfast/app-proot/' + root_id + '/planning'
    return {'root_id': root_id, 'current': read('cat', directory + '/current'),
            'blobs': read('ls', '-l', directory + '/blobs/sha256'),
            'snapshots': read('ls', directory + '/snapshots')}

results = []
for index, action in enumerate(['check', 'refresh', 'install', 'verify', 'refresh']):
    source = root / 'evidence' / ('dnfast-product-' + args.candidate + '-' + action + '.json')
    previous = source.stat().st_mtime_ns if source.exists() else None
    # The existing runner reidentifies hardware, staged hashes and installed APK at every step.
    run = subprocess.run([sys.executable, '-I', '-S', '-X', 'utf8',
                          str(Path(__file__).with_name('run-product-probe.py')), action, *common],
                         cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    name = f'{index + 1:02d}-{action}'
    (target / (name + '.log')).write_bytes(run.stdout)
    result = {'step': name, 'runner_exit': run.returncode}
    if source.exists() and source.stat().st_mtime_ns != previous:
        data = source.read_bytes()
        (target / (name + '.json')).write_bytes(data)
        result['elapsed_seconds'] = json.loads(data).get('elapsed_seconds')
    results.append(result)
    (target / (name + '-planning-state.json')).write_text(json.dumps(planning_state(), indent=2))
    (target / 'summary.json').write_text(json.dumps(results, indent=2))
    print(json.dumps(result), flush=True)
    if run.returncode:
        print('Stopped; evidence retained at ' + str(target), flush=True)
        sys.exit(run.returncode)
print('Fixed reproduction cycle passed: ' + str(target), flush=True)

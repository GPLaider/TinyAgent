"""Authorized Lyriq1 short screen-off probe; no unlock or power-policy edits."""
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
ADB = Path.home() / 'AppData/Local/Android/Sdk/platform-tools/adb.exe'
SERIAL = '100.79.134.53:5555'

def run(*args):
    return subprocess.check_output([str(a) for a in args], timeout=45).decode().strip()

def adb(*args):
    return run(ADB, '-s', SERIAL, *args)

def web(*args):
    return json.loads(run('C:/Program Files/nodejs/node.exe', ROOT / 'scripts/inspect-webview-theme-raw.mjs', *args))

assert adb('shell', 'getprop', 'ro.serialno') == 'ZY22J58799'
before = web('backend-summary')
assert not before['status'], 'Existing work active'
report = {'serial': SERIAL, 'before': before, 'scope':
    'Three 65-second shell jobs under screen-off; ADB observation, not long Doze or model inference', 'rounds': []}
destination = ROOT / 'evidence/lyriq1-screen-off-runtime.json'
assert not destination.exists(), 'Preserve previous evidence before another run'
apk = adb('shell', 'pm', 'path', 'io.github.gplaider.tinyagent.debug').removeprefix('package:')
report['apk_sha256'] = adb('shell', 'sha256sum', apk).split()[0]
def save():
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

for number in range(1, 4):
    sid = web('screen-off-job-start')['session']
    entry = {'round': number, 'session': sid, 'samples': [], 'passed': False}
    report['rounds'].append(entry)
    save()
    deadline = time.monotonic() + 10
    while not any(line.split()[-1:] == ['sleep'] for line in adb('shell', 'ps', '-A', '-o', 'UID,PID,PPID,NAME').splitlines() if line.split()[:1] == ['10042']):
        assert time.monotonic() < deadline, 'Job did not start'
        time.sleep(.2)
    adb('shell', 'input', 'keyevent', '223')
    samples = []
    for sample in range(3):
        time.sleep(20)
        power = adb('shell', 'dumpsys', 'power')
        assert any('mWakefulness=' + state in power for state in ('Asleep', 'Dozing')), 'Device became interactive'
        assert 'mHoldingDisplaySuspendBlocker=false' in power, 'Display suspend blocker held'
        ps = '\n'.join(line for line in adb('shell', 'ps', '-A', '-o', 'UID,PID,PPID,NAME').splitlines() if line.split()[:1] == ['10042'])
        assert any(line.split()[-1:] == ['sleep'] for line in ps.splitlines()), 'Sleep process missing'
        samples.append({'elapsed': 20 * (sample + 1), 'processes': ps,
            'power': [line.strip() for line in power.splitlines() if 'mWakefulness=' in line or 'TinyAgent:LocalRuntime' in line]})
        entry['samples'] = samples
        save()
        print(f'round={number} screen-off={20 * (sample + 1)}s process alive', flush=True)
    time.sleep(8)
    power = adb('shell', 'dumpsys', 'power')
    assert any('mWakefulness=' + state in power for state in ('Asleep', 'Dozing'))
    wake_ms = int(adb('shell', 'date', '+%s')) * 1000
    entry['wake_ms'] = wake_ms
    save()
    adb('shell', 'input', 'keyevent', '224')
    after = web('probe-session', sid)
    states = [p['state'] for m in after['messages'] for p in m['parts'] if p['type'] == 'tool']
    assert len(states) == 1 and states[0]['status'] == 'completed', states
    assert states[0].get('metadata', {}).get('exit') == 0, states
    assert states[0]['time']['end'] < wake_ms, 'Completion not proven before wake'
    assert after['status']['type'] == 'idle'
    entry.update(state=states[0], passed=True)
    save()
    print(f'round={number} PASS completed before wake', flush=True)
report['passed'] = True
save()

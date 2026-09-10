"""Three real Lyriq1 native stop/restart rounds; only dedicated sleep jobs."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
ADB = Path.home() / 'AppData/Local/Android/Sdk/platform-tools/adb.exe'
SERIAL = '100.79.134.53:5555'
NODE = Path('C:/Program Files/nodejs/node.exe')
evidence = ROOT / 'evidence'

def run(*args):
    return subprocess.check_output([str(a) for a in args], timeout=90).decode('utf-8')

def adb(*args):
    return run(ADB, '-s', SERIAL, *args)

def ui(*args):
    return run(sys.executable, '-I', '-S', '-X', 'utf8', ROOT / 'scripts/device-ui.py', SERIAL, *args)

def web(*args):
    return run(NODE, ROOT / 'scripts/inspect-webview-theme-raw.mjs', *args)

assert adb('shell', 'getprop', 'ro.serialno').strip() == 'ZY22J58799'
rounds = []
for number in range(1, 4):
    sid = json.loads(web('recovery-job-start'))['session']
    print(f'round={number} started {sid}', flush=True)
    deadline = time.monotonic() + 15
    while True:
        processes = adb('shell', 'ps', '-u', '10042', '-o', 'PID,PPID,NAME')
        sleeps = [line.split()[0] for line in processes.splitlines() if line.split()[-1:] == ['sleep']]
        if sleeps:
            assert len(sleeps) == 1
            break
        assert time.monotonic() < deadline, 'Sleep child not observed'
        time.sleep(.5)
    before = json.loads(web('probe-session', sid))
    assert before['status']['type'] == 'busy'
    shutil.copyfile(evidence / (sid + '-probe.json'), evidence / f'native-recovery-round-{number}-before.json')
    ui('--tap', '작업 환경')
    ui('--tap', '진단 정보  ＋')
    ui('--tap', '로컬 백엔드 중단')
    deadline = time.monotonic() + 10
    while True:
        stopped = adb('shell', 'ps', '-u', '10042', '-o', 'PID,PPID,NAME')
        names = [line.split()[-1] for line in stopped.splitlines()[1:]]
        if names == ['io.github.gplaider.tinyagent.debug']:
            break
        assert time.monotonic() < deadline, 'App-owned subprocess still alive'
        time.sleep(.5)
    ui('--tap', '환경 준비하기')
    deadline = time.monotonic() + 60
    while '환경 준비 완료' not in ui():
        assert time.monotonic() < deadline, 'Backend preparation did not finish'
        time.sleep(1)
    # Progress layout changes move controls. Fold only after preparation settles.
    if '진단 정보  −' in ui():
        ui('--tap', '진단 정보  −')
    ui('--tap', '대화 시작하기')
    after = json.loads(web('probe-session', sid))
    shutil.copyfile(evidence / (sid + '-probe.json'), evidence / f'native-recovery-round-{number}-after.json')
    assert after['status']['type'] == 'idle'
    parts = [p for m in after['messages'] for p in m['parts'] if p['type'] == 'tool']
    assert len(parts) == 1
    state = parts[0]['state']
    assert state['status'] == 'error' and state['metadata']['interrupted'] is True
    assert state['metadata']['recovery'] == 'runtime-restarted'
    rounds.append({'round': number, 'session': sid, 'before_ps': processes, 'stopped_ps': stopped,
                   'actual_processes_stopped': True, 'persisted_tool_recovered': True})
    (evidence / 'lyriq1-native-stop-recovery-rounds.json').write_text(json.dumps(rounds, indent=2))
    print(f'round={number} PASS process exit + automatic stored-state recovery', flush=True)
print('PASS: 3 native stop/restart rounds; no manual abort cleanup used', flush=True)

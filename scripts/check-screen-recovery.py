"""USB Pacman: screen off/on and background/foreground preserve live sessions."""
import argparse
import base64
import json
from pathlib import Path
import subprocess
import time
import urllib.request
import http.client

ROOT = Path(__file__).resolve().parents[1]
ADB = Path.home() / 'AppData/Local/Android/Sdk/platform-tools/adb.exe'
parser = argparse.ArgumentParser()
parser.add_argument('--lyriq2', action='store_true')
parser.add_argument('--off-seconds', type=int, default=15)
parser.add_argument('--keep-locked', action='store_true', help='Do not dismiss keyguard or return the UI to foreground')
args = parser.parse_args()
assert 15 <= args.off_seconds <= 600
SERIAL = '100.79.65.42:5555' if args.lyriq2 else '000501423003390'
PORT = 14098 if args.lyriq2 else 14097
PACKAGE = 'io.github.gplaider.tinyagent.debug'
def adb(*args):
    return subprocess.check_output([str(ADB), '-s', SERIAL, *args], timeout=30).decode().strip()
assert adb('shell', 'getprop', 'ro.serialno') == ('ZY22HZPLL8' if args.lyriq2 else SERIAL)
assert 'deviceLocked=0' in adb('shell', 'dumpsys', 'trust')
adb('forward', 'tcp:'+str(PORT), 'tcp:4097')
secret = adb('exec-out', 'run-as', PACKAGE, 'cat', 'no_backup/stock-backend-auth')
assert len(secret) == 64
auth = 'Basic '+base64.b64encode(('opencode:'+secret).encode()).decode()
def request(path, payload=None, timeout=30):
    req = urllib.request.Request('http://127.0.0.1:'+str(PORT)+path,
        data=None if payload is None else json.dumps(payload).encode(),
        headers={'Authorization':auth, 'Content-Type':'application/json', 'x-opencode-directory':'/workspace'})
    with urllib.request.urlopen(req, timeout=timeout) as response: return json.load(response)
deadline = time.monotonic() + 90
while True:
    try:
        if request('/global/health', timeout=5)['healthy']: break
    except (OSError, http.client.HTTPException):
        pass
    assert time.monotonic() < deadline, 'Backend did not become ready within 90 seconds'
    time.sleep(1)
assert not request('/session/status'), 'Existing backend work active; do not disturb it'
sessions = [request('/session', {'title':'검증 · 화면 복구 '+str(i)}) for i in range(3)]
results = []
try:
    for i in range(3):
        adb('shell','input','keyevent','3')
        assert request('/global/health')['healthy']
        adb('shell','input','keyevent','223')
        print('screen recovery', i+1, 'screen-off wait', args.off_seconds, 'seconds', flush=True)
        time.sleep(args.off_seconds)
        power = adb('shell','dumpsys','power')
        assert 'mWakefulness=Asleep' in power or 'mWakefulness=Dozing' in power
        assert request('/global/health')['healthy']
        result = request('/session/'+sessions[i]['id']+'/shell',
                         {'agent':'build', 'command':'/usr/bin/sha256sum /usr/bin/git'})
        output = '\n'.join(p.get('state',{}).get('output','') for p in result['parts'] if p['type']=='tool')
        assert '/usr/bin/git' in output and len(output.split()[0]) == 64, output
        for session in sessions:
            assert request('/session/'+session['id'])['title'] == session['title']
        if not args.keep_locked:
            adb('shell','input','keyevent','224')
            adb('shell','wm','dismiss-keyguard')
            adb('shell','am','start','-n',PACKAGE+'/io.github.gplaider.tinyagent.AppActivity')
        assert request('/global/health')['healthy']
        results.append(dict(iteration=i+1, screen_off_health=True, background_health=True, sessions_preserved=3, screen_off_command_output=output))
        print('screen recovery', i+1, 'passed', flush=True)
except Exception as error:
    (ROOT/f'evidence/screen-recovery-failure-{int(time.time())}.json').write_text(json.dumps(
        dict(serial=SERIAL, off_seconds=args.off_seconds, completed_rounds=results,
             error_type=type(error).__name__, outcome='failed'),indent=2)+'\n')
    raise
finally:
    if not args.keep_locked:
        adb('shell','input','keyevent','224')
        adb('shell','wm','dismiss-keyguard')
    adb('forward','--remove','tcp:'+str(PORT))
apk = adb('shell','pm','path',PACKAGE).removeprefix('package:')
device = 'lyriq2' if args.lyriq2 else 'pacman'
(ROOT/f'evidence/{device}-screen-recovery-{args.off_seconds}s-{int(time.time())}.json').write_text(json.dumps(dict(serial=SERIAL, apk_sha256=adb('shell','sha256sum',apk).split()[0], results=results, kept_locked=args.keep_locked, scope=f'{args.off_seconds}-second screen-off observations, real Fedora command while off; not long Doze or UI restoration acceptance'),indent=2)+'\n')

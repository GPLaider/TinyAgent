"""USB Pacman: screen off/on and background/foreground preserve live sessions."""
import base64
import json
from pathlib import Path
import subprocess
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
ADB = Path.home() / 'AppData/Local/Android/Sdk/platform-tools/adb.exe'
SERIAL = 'USB_TEST_SERIAL'
PACKAGE = 'io.github.gplaider.tinyagent.debug'
def adb(*args):
    return subprocess.check_output([str(ADB), '-s', SERIAL, *args], timeout=30).decode().strip()
assert adb('shell', 'getprop', 'ro.serialno') == SERIAL
assert 'deviceLocked=0' in adb('shell', 'dumpsys', 'trust')
adb('forward', 'tcp:14097', 'tcp:4097')
secret = adb('exec-out', 'run-as', PACKAGE, 'cat', 'no_backup/stock-backend-auth')
assert len(secret) == 64
auth = 'Basic '+base64.b64encode(('opencode:'+secret).encode()).decode()
def request(path, payload=None):
    req = urllib.request.Request('http://127.0.0.1:14097'+path,
        data=None if payload is None else json.dumps(payload).encode(),
        headers={'Authorization':auth, 'Content-Type':'application/json', 'x-opencode-directory':'/workspace'})
    with urllib.request.urlopen(req, timeout=30) as response: return json.load(response)
sessions = [request('/session', {'title':'검증 · 화면 복구 '+str(i)}) for i in range(3)]
results = []
try:
    for i in range(3):
        adb('shell','input','keyevent','3')
        assert request('/global/health')['healthy']
        adb('shell','input','keyevent','223')
        time.sleep(5)
        power = adb('shell','dumpsys','power')
        assert 'mWakefulness=Asleep' in power or 'mWakefulness=Dozing' in power
        assert request('/global/health')['healthy']
        for session in sessions:
            assert request('/session/'+session['id'])['title'] == session['title']
        adb('shell','input','keyevent','224')
        adb('shell','wm','dismiss-keyguard')
        adb('shell','am','start','-n',PACKAGE+'/io.github.gplaider.tinyagent.AppActivity')
        assert request('/global/health')['healthy']
        results.append(dict(iteration=i+1, screen_off_health=True, background_health=True, sessions_preserved=3))
        print('screen recovery', i+1, 'passed', flush=True)
finally:
    adb('shell','input','keyevent','224')
    adb('shell','wm','dismiss-keyguard')
apk = adb('shell','pm','path',PACKAGE).removeprefix('package:')
(ROOT/'evidence/screen-recovery-v12.json').write_text(json.dumps(dict(serial=SERIAL, apk_sha256=adb('shell','sha256sum',apk).split()[0], results=results, scope='Five-second screen-off and background cycles; not credential lock, long Doze or UI scroll acceptance'),indent=2)+'\n')

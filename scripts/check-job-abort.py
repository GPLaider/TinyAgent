"""Three actual backend aborts; verify disappearance of each Android process."""
import base64
import concurrent.futures
import json
from pathlib import Path
import subprocess
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
ADB = Path.home() / 'AppData/Local/Android/Sdk/platform-tools/adb.exe'
SERIAL = '192.0.2.2:5555'
PACKAGE = 'io.github.gplaider.tinyagent.debug'
SHARED = '/data/user/0/' + PACKAGE + '/files/linux/shared/'
def adb(*args):
    return subprocess.check_output([str(ADB), '-s', SERIAL, *args], timeout=30).decode().strip()
assert adb('shell', 'getprop', 'ro.serialno') == 'EDGE40_ROOT_SERIAL'
adb('push', str(ROOT/'scripts/recovery-job.sh'), SHARED+'recovery-job.sh')
adb('shell', 'chmod', '644', SHARED+'recovery-job.sh')
adb('forward', 'tcp:14098', 'tcp:4097')
secret = adb('exec-out', 'run-as', PACKAGE, 'cat', 'no_backup/stock-backend-auth')
assert len(secret) == 64
auth = 'Basic ' + base64.b64encode(('opencode:'+secret).encode()).decode()
def request(path, payload=None):
    req = urllib.request.Request('http://127.0.0.1:14098'+path,
        data=None if payload is None else json.dumps(payload).encode(),
        headers={'Authorization': auth, 'Content-Type':'application/json', 'x-opencode-directory':'/workspace'})
    with urllib.request.urlopen(req, timeout=150) as response:
        return json.load(response)
results = []
with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
    for iteration in range(3):
        adb('shell', 'rm', '-f', SHARED+'recovery-job.pid')
        session = request('/session', {'title':'검증 · 실제 프로세스 중단'})['id']
        future = executor.submit(request, '/session/'+session+'/shell',
                                 {'agent':'build', 'command':'/usr/bin/bash /shared/recovery-job.sh'})
        pid = None
        for attempt in range(30):
            if subprocess.run([str(ADB), '-s', SERIAL, 'shell', 'test', '-f', SHARED+'recovery-job.pid'], capture_output=True).returncode == 0:
                pid = int(adb('shell', 'cat', SHARED+'recovery-job.pid'))
                break
            time.sleep(1)
        assert pid is not None
        assert 'sleep' in adb('shell', 'cat', '/proc/'+str(pid)+'/comm')
        started = time.monotonic()
        request('/session/'+session+'/abort', {})
        future.result(timeout=15)
        for attempt in range(15):
            alive = subprocess.run([str(ADB), '-s', SERIAL, 'shell', 'test', '-d', '/proc/'+str(pid)], capture_output=True).returncode == 0
            if not alive: break
            time.sleep(1)
        assert not alive, 'Aborted process survived'
        assert request('/global/health')['healthy']
        assert request('/session/'+session)['id'] == session
        results.append(dict(iteration=iteration+1, session=session, pid=pid, process_gone=True, seconds=round(time.monotonic()-started,2)))
        print('abort', iteration+1, 'passed', flush=True)
apk = adb('shell', 'pm', 'path', PACKAGE).removeprefix('package:')
(ROOT/'evidence/job-abort-v12.json').write_text(json.dumps(dict(serial='EDGE40_ROOT_SERIAL', apk_sha256=adb('shell','sha256sum',apk).split()[0], results=results), indent=2)+'\n')

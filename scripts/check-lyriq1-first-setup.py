"""First real app preparation on Lyriq 1; ADB observes but never prepares Fedora."""
import base64
import json
from pathlib import Path
import re
import subprocess
import time
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ADB = Path.home()/'AppData/Local/Android/Sdk/platform-tools/adb.exe'
TARGET = '100.79.134.53:5555'
PACKAGE = 'io.github.gplaider.tinyagent.debug'
def adb(*args): return subprocess.check_output([str(ADB),'-s',TARGET,*args],timeout=40)
def exists(path):
    return subprocess.run([str(ADB),'-s',TARGET,'shell','run-as',PACKAGE,'test','-e',path],capture_output=True,timeout=30).returncode == 0
def tree():
    adb('shell','uiautomator','dump','/data/local/tmp/tinyagent-first-ui.xml')
    return ET.fromstring(adb('shell','cat','/data/local/tmp/tinyagent-first-ui.xml'))
def tap(node):
    assert node.get('enabled') == 'true'
    x1,y1,x2,y2 = map(int,re.findall(r'\d+',node.get('bounds')))
    assert x2>x1 and y2>y1
    adb('shell','input','tap',str((x1+x2)//2),str((y1+y2)//2))
assert adb('shell','getprop','ro.serialno').decode().strip() == 'ZY22J58799'
assert adb('shell','id').decode().startswith('uid=2000(')
assert adb('shell','getenforce').decode().strip() == 'Enforcing'
assert int(adb('shell','run-as',PACKAGE,'id','-u').decode().strip()) >= 10000, 'App-private observer access unavailable'
assert 'deviceLocked=0' in adb('shell','dumpsys','trust').decode(), 'Unlock Lyriq 1 before real UI validation'
assert not exists('files/linux/prepared-v1'), 'This is no longer a first preparation; do not clear user data'
assert not exists('no_backup/adb-identity'), 'Unexpected app ADB identity before test'
adb('shell','am','start','-n',PACKAGE+'/io.github.gplaider.tinyagent.AppActivity')
nodes = tree()
root = next(n for n in nodes.iter('node') if n.get('text') == 'Root 실행 허용')
assert root.get('checked') == 'false'
tap(next(n for n in nodes.iter('node') if n.get('text') == '환경 준비하기'))
started = time.monotonic()
last = None
while time.monotonic()-started < 600:
    if exists('shared_prefs/runtime.xml'):
        prefs = ET.fromstring(adb('shell','run-as',PACKAGE,'cat','shared_prefs/runtime.xml'))
        status = next((n.text for n in prefs if n.get('name') == 'status'),'')
        if status != last: print(status,flush=True); last=status
        if status.startswith('환경 준비 실패'): raise AssertionError(status)
        if status.startswith('Fedora 설치 완료'): break
    time.sleep(3)
else: raise AssertionError('First preparation timed out')
assert not exists('no_backup/adb-identity'), 'App attempted ADB authentication'
assert exists('files/linux/prepared-v1')
rows = [line.split() for line in adb('shell','ps','-A','-o','UID,PID,PPID,NAME').decode().splitlines()[1:]]
app = next(row for row in rows if row[3] == PACKAGE)
assert int(app[0])>=10000
linux = [row for row in rows if row[0] == app[0] and row[3] in ('libproot.so','opencode')]
assert len(linux) == 2
adb('forward','tcp:14099','tcp:4097')
secret = adb('exec-out','run-as',PACKAGE,'cat','no_backup/stock-backend-auth').strip()
assert len(secret)==64
req = urllib.request.Request('http://127.0.0.1:14099/global/health',headers={'Authorization':'Basic '+base64.b64encode(b'opencode:'+secret).decode()})
with urllib.request.urlopen(req,timeout=15) as response: assert json.load(response)['healthy']
apk=adb('shell','pm','path',PACKAGE).decode().strip().removeprefix('package:')
report=dict(serial='ZY22J58799',apk_sha256=adb('shell','sha256sum',apk).decode().split()[0],first_prepare=True,
            root_selected=False,app_adb_identity_created=False,app_uid=int(app[0]),processes=linux,
            backend_healthy=True,seconds=round(time.monotonic()-started,1),scope='ADB-connected observer; actual app UID preparation without app self-ADB. Custom ROM, not Flip7.')
(ROOT/'evidence/lyriq1-first-setup-v16.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))

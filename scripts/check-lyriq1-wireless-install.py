"""Three actual app TLS installs; observe UI and PackageManager, no run-as."""
import json
from pathlib import Path
import re
import subprocess
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ADB = str(Path.home()/'AppData/Local/Android/Sdk/platform-tools/adb.exe')
SERIAL = '100.79.134.53:5555'
PACKAGE = 'io.github.gplaider.tinyagent.debug'
FIXTURE = 'io.github.gplaider.tinyagent.installfixture'
def adb(*args): return subprocess.check_output([ADB,'-s',SERIAL,*args],timeout=40).decode().strip()
def tree(): return ET.fromstring(re.search(r'<hierarchy.*</hierarchy>',adb('exec-out','uiautomator','dump','/dev/tty'),re.S).group())
def tap(label):
    node = next(n for n in tree().iter('node') if n.get('text')==label)
    x1,y1,x2,y2 = map(int,re.findall(r'\d+',node.get('bounds')))
    assert x2>x1 and y2>y1
    adb('shell','input','tap',str((x1+x2)//2),str((y1+y2)//2))
assert adb('shell','getprop','ro.serialno')=='ZY22J58799'
assert any(n.get('text')=='Developer · self-ADB' for n in tree().iter('node'))
report = []
for i in range(3):
    before = adb('shell','pm','path',FIXTURE)
    tap('파일에서 APK 선택'); tap('tinyagent-install-check.apk')
    for _ in range(25):
        texts = [n.get('text','') for n in tree().iter('node')]
        failure = next((t for t in texts if t.startswith('설치 실패')),None)
        assert not failure,failure
        current = adb('shell','pm','path',FIXTURE)
        if current != before and any(t.startswith('설치 완료 · '+FIXTURE) for t in texts): break
        time.sleep(2)
    else: raise AssertionError('New PackageManager installation not observed')
    digest = adb('shell','sha256sum',current.removeprefix('package:')).split()[0]
    report.append(dict(round=i+1,installed_sha256=digest,route='app wireless TLS ADB'))
    print('Verified in-app wireless installation',i+1,flush=True)
apk = adb('shell','pm','path',PACKAGE).removeprefix('package:')
result = dict(serial='ZY22J58799',apk_sha256=adb('shell','sha256sum',apk).split()[0],results=report)
(ROOT/'evidence/lyriq1-wireless-install.json').write_text(json.dumps(result,indent=2),encoding='utf-8')

"""Reconnect three times through UI, then rotate Android's wireless port through UI."""
import json
from pathlib import Path
import re
import subprocess
import time
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ADB = str(Path.home()/'AppData/Local/Android/Sdk/platform-tools/adb.exe')
SERIAL = '100.79.134.53:5555'
version = sys.argv[1] if len(sys.argv)>1 else 'v18'
assert re.fullmatch(r'v\d+',version)
def adb(*args): return subprocess.check_output([ADB,'-s',SERIAL,*args],timeout=40)
def tree():
    raw = adb('exec-out','uiautomator','dump','/dev/tty').decode()
    return ET.fromstring(re.search(r'<hierarchy.*</hierarchy>',raw,re.S).group())
def tap(text):
    nodes = list(tree().iter('node'))
    matches = [n for n in nodes if n.get('text')==text]
    assert matches, 'Missing UI control: '+text
    node = matches[0]
    x1,y1,x2,y2 = map(int,re.findall(r'\d+',node.get('bounds')))
    assert x2>x1 and y2>y1
    adb('shell','input','tap',str((x1+x2)//2),str((y1+y2)//2))
def reconnect():
    tap('기존 페어링으로 다시 연결')
    for _ in range(18):
        texts = [n.get('text','') for n in tree().iter('node')]
        status = next((t for t in texts if t.startswith(('✓ Developer 확인 완료','Developer 연결 실패'))),None)
        if status:
            assert status.startswith('✓ Developer 확인 완료'),status
            return status
        time.sleep(2)
    raise AssertionError('Wireless reconnect timed out')
assert adb('shell','getprop','ro.serialno').decode().strip()=='ZY22J58799'
results = []
for i in range(3):
    results.append(dict(round=i+1,status=reconnect()))
    print('Verified wireless reconnect',i+1,flush=True)
(ROOT/f'evidence/lyriq1-{version}-wireless-reconnect.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')

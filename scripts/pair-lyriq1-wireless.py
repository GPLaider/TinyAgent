"""Exercise Android pairing -> TinyAgent notification. Never print/store the code."""
import subprocess
from pathlib import Path
import re
import time
import xml.etree.ElementTree as ET

ADB = str(Path.home()/'AppData/Local/Android/Sdk/platform-tools/adb.exe')
SERIAL = '100.79.134.53:5555'
def adb(*args):
    result = subprocess.run([ADB,'-s',SERIAL,*args],capture_output=True,timeout=40)
    if result.returncode: raise RuntimeError('ADB UI operation failed; arguments withheld')
    return result.stdout
def tree():
    raw = adb('exec-out','uiautomator','dump','/dev/tty').decode()
    return ET.fromstring(re.search(r'<hierarchy.*</hierarchy>',raw,re.S).group())
def tap(node):
    x1,y1,x2,y2 = map(int,re.findall(r'\d+',node.get('bounds')))
    assert x2>x1 and y2>y1
    adb('shell','input','tap',str((x1+x2)//2),str((y1+y2)//2))
assert adb('shell','getprop','ro.serialno').decode().strip()=='ZY22J58799'
nodes = tree()
button = next(n for n in nodes.iter('node') if n.get('text')=='페어링 코드로 기기 페어링')
tap(button)
nodes = tree()
codes = [re.sub(r'\s','',n.get('text','')) for n in nodes.iter('node')
         if n.get('package')=='com.android.settings' and re.fullmatch(r'\d{6}',re.sub(r'\s','',n.get('text','')))]
assert len(codes)==1, 'Expected one Android pairing code; no private UI output recorded'
code = codes[0]
adb('shell','cmd','statusbar','expand-notifications')
nodes = tree()
buttons = [n for n in nodes.iter('node') if n.get('text')=='코드 입력']
assert len(buttons)==1, 'TinyAgent pairing notification input not visible'
tap(buttons[0])
nodes = tree()
field = next(n for n in nodes.iter('node') if n.get('class')=='android.widget.EditText' and n.get('package')=='com.android.systemui')
tap(field)
adb('shell','input','text',code)
code = None; codes.clear()
nodes = tree()
send = next(n for n in nodes.iter('node') if n.get('resource-id','').endswith('/remote_input_send'))
tap(send)
adb('shell','cmd','statusbar','collapse')
print('Pairing code submitted through the actual TinyAgent notification; code not retained')

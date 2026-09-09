"""Real-device workspace export regression; begin on the APK installation screen."""
import subprocess
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ADB = str(Path.home() / 'AppData/Local/Android/Sdk/platform-tools/adb.exe')
SERIAL = '100.79.134.53:5555'
def run(*args):
    return subprocess.check_output([ADB, '-s', SERIAL, *args], timeout=30).decode('utf-8')
def ui():
    run('shell', 'uiautomator', 'dump', '/sdcard/tinyagent-ui.xml')
    return ET.fromstring(run('shell', 'cat', '/sdcard/tinyagent-ui.xml'))
def tap(node):
    x1,y1,x2,y2=map(int,re.findall(r'\d+',node.get('bounds')))
    assert x2>x1 and y2>y1
    run('shell','input','tap',str((x1+x2)//2),str((y1+y2)//2))
def label(text):
    nodes=[n for n in ui().iter('node') if n.get('text')==text]
    assert len(nodes)==1, text
    tap(nodes[0])
def enter(text):
    fields=[n for n in ui().iter('node') if n.get('class')=='android.widget.EditText']
    assert len(fields)==1
    tap(fields[0])
    run('shell','input','keycombination','KEYCODE_CTRL_LEFT','KEYCODE_A')
    run('shell','input','text',text)
    run('shell','input','keyevent','KEYCODE_BACK')

assert run('shell','getprop','ro.serialno').strip()=='ZY22J58799'
enter('../')
label('작업공간 파일 내보내기')
assert any('작업공간 안의 파일' in n.get('text','') for n in ui().iter('node'))
print('PASS: path outside workspace rejected')
enter('Ventoid/app/build/outputs/apk/debug/app-debug.apk')
label('작업공간 파일 내보내기')
tree=ui()
assert any(n.get('package')=='com.android.documentsui' for n in tree.iter('node'))
print('PASS: real Android save dialog opened; inspect destination before saving')

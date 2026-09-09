"""Check the visible APK popover after a real path tap; does not send/install files."""
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

adb = 'C:/Users/Administrator/AppData/Local/Android/Sdk/platform-tools/adb.exe'
serial = sys.argv[1]
def shell(*args):
    return subprocess.check_output([adb, '-s', serial, 'shell', *args], encoding='utf-8')
shell('uiautomator', 'dump', '/sdcard/tinyagent-popover.xml')
root = ET.fromstring(shell('cat', '/sdcard/tinyagent-popover.xml'))
nodes = {n.get('text'): n for n in root.iter('node') if n.get('text') in ['설치', '저장', '공유']}
assert set(nodes) == {'설치', '저장', '공유'}, 'APK action menu missing'
bounds = {key: list(map(int, re.findall(r'\d+', n.get('bounds')))) for key,n in nodes.items()}
assert len({v[1] for v in bounds.values()}) == 1, 'Actions must share one horizontal row'
assert all(v[2]>v[0] and v[3]>v[1] for v in bounds.values())
width = max(v[2] for v in bounds.values())-min(v[0] for v in bounds.values())
screen_width = int(re.findall(r'(\d+)x\d+', shell('wm','size'))[-1])
assert width < screen_width * .6, 'Menu is too wide'
assert not any(n.get('text') == '닫기' for n in root.iter('node')), 'Outside tap replaces a bulky close row'
report = {'serial':serial, 'actions':bounds, 'width':width, 'screenWidth':screen_width}
path = Path(__file__).resolve().parents[1] / 'evidence' / (sys.argv[2]+'.json')
path.write_text(json.dumps(report, ensure_ascii=False, indent=2),encoding='utf-8')
print(json.dumps(report, ensure_ascii=False))

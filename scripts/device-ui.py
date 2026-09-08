"""Inspect or tap one visible UI label on an explicitly selected test phone."""
import argparse
from pathlib import Path
import subprocess
import re
import xml.etree.ElementTree as ET

parser = argparse.ArgumentParser()
parser.add_argument('serial', choices=['USB_TEST_SERIAL', '192.0.2.2:5555'])
parser.add_argument('--tap')
args = parser.parse_args()
adb = str(Path.home() / 'AppData/Local/Android/Sdk/platform-tools/adb.exe')
def run(*command):
    return subprocess.check_output([adb, '-s', args.serial, *command], timeout=30)
run('shell', 'uiautomator', 'dump', '/sdcard/tinyagent-ui.xml')
tree = ET.fromstring(run('shell', 'cat', '/sdcard/tinyagent-ui.xml'))
if args.tap:
    matches = [n for n in tree.iter('node') if args.tap in (n.get('text'), n.get('content-desc'))]
    assert len(matches) == 1, 'Expected one visible label: ' + args.tap
    x1,y1,x2,y2 = map(int, re.findall(r'\d+', matches[0].get('bounds')))
    assert x2>x1 and y2>y1
    run('shell', 'input', 'tap', str((x1+x2)//2), str((y1+y2)//2))
    print('Tapped:', args.tap)
else:
    for node in tree.iter('node'):
        label = node.get('text') or node.get('content-desc')
        if label: print(label, node.get('bounds'))

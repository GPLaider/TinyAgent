"""Inspect or tap one visible UI label on an explicitly selected test phone."""
import argparse
from pathlib import Path
import subprocess
import re
import xml.etree.ElementTree as ET

parser = argparse.ArgumentParser()
parser.add_argument('serial', choices=['000501423003390', '100.79.65.42:5555', '100.79.134.53:5555'])
parser.add_argument('--tap')
parser.add_argument('--screenshot', help='Evidence filename stem')
parser.add_argument('--capture-only', action='store_true', help='Capture transient controls without waiting for UI idle')
args = parser.parse_args()
adb = str(Path.home() / 'AppData/Local/Android/Sdk/platform-tools/adb.exe')
def run(*command):
    return subprocess.check_output([adb, '-s', args.serial, *command], timeout=30)
def capture():
    assert args.screenshot and re.fullmatch(r'[A-Za-z0-9-]+', args.screenshot)
    image = Path(__file__).resolve().parents[1]/'evidence'/(args.screenshot+'.png')
    image.write_bytes(run('exec-out', 'screencap', '-p'))
    print(image)
if args.capture_only:
    assert not args.tap
    capture()
    raise SystemExit(0)
assert b'UI hierchary dumped to:' in run('shell', 'uiautomator', 'dump', '/sdcard/tinyagent-ui.xml'), 'Fresh UI dump failed; do not use a stale tree'
tree = ET.fromstring(run('shell', 'cat', '/sdcard/tinyagent-ui.xml'))
if args.tap:
    matches = [n for n in tree.iter('node') if args.tap in (n.get('text'), n.get('content-desc'))]
    assert len(matches) == 1, 'Expected one visible label: ' + args.tap
    x1,y1,x2,y2 = map(int, re.findall(r'\d+', matches[0].get('bounds')))
    assert x2>x1 and y2>y1
    # This test device missed instantaneous injected taps; a 120ms press reproduced normal touch.
    x,y=str((x1+x2)//2),str((y1+y2)//2)
    run('shell', 'input', 'touchscreen', 'swipe', x,y,x,y,'120')
    print('Tapped:', args.tap)
else:
    for node in tree.iter('node'):
        label = node.get('text') or node.get('content-desc')
        if label: print(label, node.get('bounds'))
if args.screenshot:
    capture()

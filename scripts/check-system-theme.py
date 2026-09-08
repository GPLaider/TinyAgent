"""Focused native/WebView system-theme captures on Pacman; restores initial system mode."""
from pathlib import Path
import json
import runpy
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ui = runpy.run_path(str(ROOT/'scripts/check-device-adb.py'))
ui['select_device']('USB_TEST_SERIAL')
adb, snapshot, tap = ui['adb'], ui['snapshot'], ui['tap']
assert adb('shell', 'getprop', 'ro.serialno').decode().strip() == 'USB_TEST_SERIAL'
out = ROOT/'evidence/system-theme-v12'
out.mkdir(exist_ok=True)
initial = adb('shell', 'cmd', 'uimode', 'night').decode().strip().split(': ')[1]
assert initial in ('yes', 'no', 'auto', 'custom')

def capture(name):
    raw = snapshot()
    (out/(name+'.xml')).write_bytes(raw)
    (out/(name+'.png')).write_bytes(adb('exec-out', 'screencap', '-p'))
    return ET.fromstring(raw)

try:
    adb('shell', 'input', 'keyevent', '224')
    adb('shell', 'wm', 'dismiss-keyguard')
    adb('shell', 'cmd', 'uimode', 'night', 'no')
    adb('shell', 'am', 'force-stop', ui['PACKAGE'])
    adb('shell', 'am', 'start', '-n', ui['PACKAGE']+'/io.github.gplaider.tinyagent.AppActivity')
    capture('native-light')
    adb('shell', 'cmd', 'uimode', 'night', 'yes')
    time.sleep(2)
    nodes = capture('native-dark')
    tap(next(n for n in nodes.iter('node') if n.get('text') == '대화 시작하기'))
    for _ in range(30):
        nodes = ET.fromstring(snapshot())
        if any(n.get('class') == 'android.webkit.WebView' for n in nodes.iter('node')): break
        time.sleep(1)
    else: raise AssertionError('WebView did not open')
    time.sleep(3)
    capture('web-dark')
    adb('shell', 'cmd', 'uimode', 'night', 'no')
    time.sleep(4)
    capture('web-light')
    (out/'result.json').write_text(json.dumps(dict(serial='USB_TEST_SERIAL', initial_mode=initial,
        scope='Actual native/WebView captures; visually inspect screenshots before claiming theme acceptance'), indent=2)+'\n')
finally:
    adb('shell', 'cmd', 'uimode', 'night', initial)

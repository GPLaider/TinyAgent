"""Fill the observed native auth dialog using this task's phone-local diagnostic secret.

Never prints or stores the password on the development host.
"""
import runpy
import time
import xml.etree.ElementTree as ET
from pathlib import Path

helpers = runpy.run_path(str(Path(__file__).with_name('check-device-adb.py')))
adb, snapshot, tap = (helpers[key] for key in ('adb', 'snapshot', 'tap'))
assert adb('shell', 'getprop', 'ro.serialno').decode().strip() == helpers['SERIAL']
adb('shell', 'input', 'keyevent', '224')
tree = ET.fromstring(snapshot())
user = next(n for n in tree.iter('node') if n.get('hint') == '백엔드 사용자 이름')
tap(user)
adb('shell', 'input', 'text', 'opencode')
tree = ET.fromstring(snapshot())
field = next(n for n in tree.iter('node') if n.get('hint') == '백엔드 암호')
secret = adb('shell', 'cat', '/data/local/tmp/tinyagent-compat-20260908/root/.tinyagent-server-password').decode().strip()
assert len(secret) == 64 and all(c in '0123456789abcdef' for c in secret)
tap(field)
adb('shell', 'input', 'text', secret)
del secret
tree = ET.fromstring(snapshot())
tap(next(n for n in tree.iter('node') if n.get('text') == '연결' and n.get('class') == 'android.widget.Button'))
for _ in range(8):
    time.sleep(1)
    result = snapshot()
    tree = ET.fromstring(result)
    if any(n.get('class') == 'android.webkit.WebView' for n in tree.iter('node')):
        if any(n.get('hint') == '백엔드 암호' for n in tree.iter('node')):
            raise RuntimeError('Backend authentication failed')
        output = helpers['ROOT'] / 'evidence' / 'backend-first-webview'
        output.mkdir(exist_ok=False)
        (output / 'ui.xml').write_bytes(result)
        (output / 'screen.png').write_bytes(adb('exec-out', 'screencap', '-p'))
        print('Backend WebView captured for inspection:', output)
        break
else:
    raise RuntimeError('WebView did not appear')

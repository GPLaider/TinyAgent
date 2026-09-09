"""Record only the test target's connectivity state and TinyAgent setup diagnostic."""
import json
import subprocess
import re
import xml.etree.ElementTree as ET
from pathlib import Path

adb = str(Path.home() / 'AppData/Local/Android/Sdk/platform-tools/adb.exe')
def run(*args):
    return subprocess.check_output([adb, '-s', '000501423003390', *args], timeout=30).decode()
assert run('shell', 'getprop', 'ro.serialno').strip() == '000501423003390'
network = re.search(r'Active default network: (.*)', run('shell', 'dumpsys', 'connectivity')).group(1)
run('shell', 'uiautomator', 'dump', '/sdcard/tinyagent-ui.xml')
texts = [n.get('text','') for n in ET.fromstring(run('shell', 'cat', '/sdcard/tinyagent-ui.xml')).iter('node')]
errors = [t for t in texts if t.startswith('환경 준비 실패:')]
report = dict(default_network=network, setup_errors=errors)
path = Path(__file__).resolve().parents[1] / 'evidence/pacman-v20-network.json'
path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(dict(default_network=network, error_prefix=[s[:200] for s in errors]), ensure_ascii=False))

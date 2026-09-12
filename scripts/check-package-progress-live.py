"""Verify package output reaches a running phone-local shell before completion."""
import base64
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import time
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
ADB = Path.home() / 'AppData/Local/Android/Sdk/platform-tools/adb.exe'
def adb(*args):
    return subprocess.check_output([str(ADB), '-s', '000501423003390', *args], timeout=30)
assert adb('shell', 'getprop', 'ro.serialno').strip() == b'000501423003390'
secret = adb('exec-out', 'run-as', 'io.github.gplaider.tinyagent.debug', 'cat', 'no_backup/stock-backend-auth').strip()
assert len(secret) == 64
adb('forward', 'tcp:14097', 'tcp:4097')
def request(path, body=None):
    req = urllib.request.Request('http://127.0.0.1:14097' + path,
        data=None if body is None else json.dumps(body).encode(),
        headers={'Authorization': 'Basic ' + base64.b64encode(b'opencode:' + secret).decode(),
                 'Content-Type': 'application/json', 'x-opencode-directory': '/workspace'})
    with urllib.request.urlopen(req, timeout=120) as response:
        return json.load(response)

assert request('/global/health')['healthy']
session = request('/session', {'title': '검증 · 패키지 중간 출력'})['id']
job = str(uuid.uuid4())
record = dict(session=session, package_job=job, samples=[])
dest = ROOT / 'evidence/package-progress-live.json'
dest.write_text(json.dumps(record, indent=2))
print(json.dumps(dict(session=session, package_job=job)), flush=True)
command = '/usr/bin/python3 /root/.tinyagent/bootstrap/tinyagent-packages.py --id ' + job + ' repo refresh'
with ThreadPoolExecutor(max_workers=1) as pool:
    future = pool.submit(request, '/session/' + session + '/shell', {'agent': 'build', 'command': command})
    for _ in range(100):
        messages = request('/session/' + session + '/message')
        for message in messages:
            for part in message.get('parts', []):
                if part.get('type') != 'tool':
                    continue
                state = part['state']
                output = state.get('output') or state.get('metadata', {}).get('output', '')
                record['samples'].append(dict(status=state['status'], bytes=len(output),
                    has_trace='dnfast-refresh-http' in output, at=time.time()))
        dest.write_text(json.dumps(record, indent=2))
        if future.done():
            break
        time.sleep(0.25)
    result = future.result()
    record['terminal'] = result
    dest.write_text(json.dumps(record, indent=2))
assert any(s['status'] == 'running' and s['has_trace'] for s in record['samples']), 'No trace observed before tool completion'
assert any(p.get('state', {}).get('metadata', {}).get('exit') == 0 for p in result['parts']), 'Refresh did not exit zero'
print('PASS: real refresh trace visible while tool running; terminal exit0')

"""Exercise the actual phone-local OpenCode API; no model call or credential output."""
import base64
import json
from pathlib import Path
import subprocess
import urllib.request
import urllib.error
import argparse

ROOT = Path(__file__).resolve().parents[1]
ADB = Path.home() / 'AppData/Local/Android/Sdk/platform-tools/adb.exe'
parser = argparse.ArgumentParser()
parser.add_argument('--serial', choices=['USB_TEST_SERIAL', '192.0.2.2:5555'], default='USB_TEST_SERIAL')
parser.add_argument('--command', default='/usr/bin/cat /etc/fedora-release')
parser.add_argument('--output', default='stock-backend-shell')
parser.add_argument('--session', help='Read progress of an existing test session instead of executing a command')
parser.add_argument('--save-session', action='store_true', help='Save all messages of the explicitly selected test session')
parser.add_argument('--abort', action='store_true', help='Abort the explicitly selected test session through the real backend')
parser.add_argument('--check-harness', action='store_true')
parser.add_argument('--catalog', action='store_true', help='Only report connected provider IDs and zero-cost model IDs; never credentials')
parser.add_argument('--prompt', help='Run an actual inference with the connected zero-cost opencode/big-pickle model')
parser.add_argument('--permissions', action='store_true', help='Inspect pending permission requests')
parser.add_argument('--approve-diagnostic-once', help='Approve only the exact Fedora identity probe in the specified --session')
parser.add_argument('--approve-harness-once', action='store_true', help='Approve only pending measured harness reads and the exact identity command, once')
args = parser.parse_args()
assert args.output.replace('-', '').isalnum()
assert all(c not in args.command for c in '\n\r;|&<>`$'), 'Use a staged script for shell grammar'
SERIAL = args.serial
PACKAGE = 'io.github.gplaider.tinyagent.debug'
def adb(*args):
    return subprocess.check_output([str(ADB), '-s', SERIAL, *args], timeout=30)
assert adb('shell', 'getprop', 'ro.serialno').decode().strip() == ('EDGE40_ROOT_SERIAL' if ':' in SERIAL else SERIAL)
PORT = 14098 if ':' in SERIAL else 14097
adb('forward', 'tcp:' + str(PORT), 'tcp:4097')
password = adb('exec-out', 'run-as', PACKAGE, 'cat', 'no_backup/stock-backend-auth').strip()
assert len(password) == 64
authorization = 'Basic ' + base64.b64encode(b'opencode:' + password).decode()
def request(path, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request('http://127.0.0.1:' + str(PORT) + path, data=data,
            headers={'Authorization': authorization, 'Content-Type': 'application/json', 'x-opencode-directory': '/workspace'})
    try:
        with urllib.request.urlopen(req, timeout=1800) as response: return json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError('Local API status=' + str(error.code) + ' ' + error.read(2000).decode()) from None

assert request('/global/health')['healthy']
if args.abort:
    assert args.session and args.session.startswith('ses_') and args.session.replace('_', '').isalnum()
    print(request('/session/' + args.session + '/abort', {}))
    raise SystemExit(0)
if args.approve_harness_once:
    assert args.session and args.session.startswith('ses_') and args.session.replace('_', '').isalnum()
    allowed_files = {'/root/.tinyagent/TINYAGENT_ENVIRONMENT.md', '/root/.tinyagent/ANDROID_TOOL.md'}
    count = 0
    for pending in request('/permission'):
        if pending['sessionID'] != args.session: continue
        metadata = pending.get('metadata', {})
        allowed = (pending['patterns'] == ['/root/.tinyagent/*'] and metadata.get('filepath') in allowed_files)
        allowed |= (pending['patterns'] == ['/etc/*'] and metadata.get('command') == 'id && cat /etc/fedora-release && pwd')
        if pending['permission'] != 'external_directory' or not allowed: continue
        assert pending['id'].replace('_', '').isalnum()
        request('/permission/'+pending['id']+'/reply', {'reply':'once'})
        count += 1
    print('Approved exact read-only probes once:', count)
    raise SystemExit(0)
if args.approve_diagnostic_once:
    pending = next(p for p in request('/permission') if p['id'] == args.approve_diagnostic_once)
    assert args.session and pending['sessionID'] == args.session
    assert pending['permission'] == 'external_directory' and pending['patterns'] == ['/etc/*']
    assert pending['metadata']['command'] == 'cat /etc/fedora-release && id && pwd'
    assert pending['id'].replace('_', '').isalnum()
    print(request('/permission/' + pending['id'] + '/reply', {'reply': 'once'}))
    raise SystemExit(0)
if args.permissions:
    print(json.dumps(request('/permission'), ensure_ascii=False, indent=2))
    raise SystemExit(0)
if args.catalog:
    catalog = request('/provider')
    connected = set(catalog.get('connected', []))
    for provider in catalog['all']:
        if provider['id'] in connected:
            models = provider.get('models', {})
            free = [key for key, value in models.items() if value.get('cost', {}).get('input') == 0 and value.get('cost', {}).get('output') == 0]
            print(json.dumps(dict(provider=provider['id'], models=len(models), zero_cost_models=free), ensure_ascii=False))
    raise SystemExit(0)
if args.check_harness:
    instructions = request('/config')['instructions']
    for name in ['AGENTS', 'STOCK', 'ADB', 'ROOT', 'TINYAGENT_ENVIRONMENT', 'ANDROID_TOOL']:
        assert '/root/.tinyagent/' + name + '.md' in instructions, name
    print('Versioned and measured harness paths loaded by actual backend')
if args.session:
    assert args.session.startswith('ses_') and args.session.replace('_', '').isalnum()
    messages = request('/session/' + args.session + '/message')
    if args.save_session:
        (ROOT / ('evidence/' + args.output + '.json')).write_text(json.dumps(dict(serial=SERIAL, session_id=args.session, messages=messages), ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    for message in messages:
        for part in message.get('parts', []):
            if part.get('type') == 'tool':
                state = part.get('state', {})
                print(state.get('status'), json.dumps(state.get('input', {}), ensure_ascii=False), str(state.get('output', state.get('metadata', {}).get('output', '')))[-1800:])
    raise SystemExit(0)
session = request('/session', {'title': '검증 · Fedora 직접 실행'})
print('Session created: ' + session['id'], flush=True)
if args.prompt:
    catalog = request('/provider')
    provider = next(p for p in catalog['all'] if p['id'] == 'opencode')
    assert 'opencode' in catalog['connected'] and provider['models']['big-pickle']['cost']['input'] == 0 and provider['models']['big-pickle']['cost']['output'] == 0
    result = request('/session/' + session['id'] + '/message', {'agent': 'build', 'model': {'providerID': 'opencode', 'modelID': 'big-pickle'}, 'parts': [{'type': 'text', 'text': args.prompt}]})
else:
    result = request('/session/' + session['id'] + '/shell', {'agent': 'build', 'command': args.command})
report = dict(serial=SERIAL, session_id=session['id'], result=result, scope='Actual opencode/big-pickle inference' if args.prompt else 'User-triggered shell API; no model inference tested')
if args.prompt: report['messages'] = request('/session/' + session['id'] + '/message')
(ROOT / ('evidence/' + args.output + '.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
if args.prompt:
    assert not result['info'].get('error'), result['info'].get('error')
    assert result['info']['tokens']['output'] > 0, 'No model output tokens'
else:
    if args.command == '/usr/bin/cat /etc/fedora-release': assert 'Fedora release 44' in json.dumps(result)
    assert any(part.get('state', {}).get('status') == 'completed' for part in result.get('parts', [])), 'Shell did not complete'
print('Phone-local OpenCode shell returned; inspect output/exit markers; session=' + session['id'])

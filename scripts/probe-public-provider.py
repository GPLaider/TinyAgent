"""Run inside diagnostic Fedora. Never print server credentials or paid-provider data."""
import base64
import json
from pathlib import Path
import urllib.request
import sys


def main():
    password = Path('/root/.tinyagent-server-password').read_text().strip()
    request = urllib.request.Request('http://127.0.0.1:4096/provider', headers={
        'Authorization': 'Basic ' + base64.b64encode(('opencode:' + password).encode()).decode(),
    })
    if '--inspect' in sys.argv or '--allow-smoke' in sys.argv:
        option = '--inspect' if '--inspect' in sys.argv else '--allow-smoke'
        session_id = sys.argv[sys.argv.index(option) + 1]
        assert session_id.startswith('ses_') and session_id.replace('_', '').isalnum()
        for path in ['/session/status', '/permission', '/session/' + session_id + '/message']:
            call = urllib.request.Request('http://127.0.0.1:4096' + path, headers=request.headers)
            with urllib.request.urlopen(call, timeout=15) as response:
                result = json.load(response)
            if path == '/permission' and option == '--allow-smoke':
                selected = [item for item in result if item.get('sessionID') == session_id]
                assert len(selected) == 1
                permission = selected[0]
                assert permission['permission'] == 'external_directory'
                assert permission['patterns'] == ['/etc/*']
                assert permission['metadata']['command'] == 'pwd; cat /etc/fedora-release'
                reply = urllib.request.Request('http://127.0.0.1:4096/permission/' + permission['id'] + '/reply',
                        data=b'{"reply":"once"}', headers={**request.headers, 'Content-Type': 'application/json'})
                with urllib.request.urlopen(reply, timeout=15) as response:
                    print('Granted the exact diagnostic read once:', response.status)
            if path.endswith('/message'):
                for message in result:
                    message['parts'] = [part for part in message.get('parts', []) if part.get('type') != 'reasoning']
            print(path, json.dumps(result, indent=2), flush=True)
        return
    with urllib.request.urlopen(request, timeout=30) as response:
        providers = json.load(response)
    free = []
    for provider in providers.get('all', []):
        if provider.get('id') != 'opencode':
            continue
        for name, model in provider.get('models', {}).items():
            cost = model.get('cost', {})
            if cost.get('input') == 0 and cost.get('output') == 0:
                free.append({'id': name, 'name': model.get('name'), 'toolcall': model.get('capabilities', {}).get('toolcall')})
    print(json.dumps({'provider': 'opencode', 'connected': 'opencode' in providers.get('connected', []),
                      'zero_cost_models': free}, indent=2))
    if '--exercise' not in sys.argv:
        return
    model = 'nemotron-3.5-lightning-free'
    assert any(item['id'] == model and item['toolcall'] for item in free)
    def post(path, body):
        call = urllib.request.Request('http://127.0.0.1:4096' + path,
                data=json.dumps(body).encode(), headers={**request.headers, 'Content-Type': 'application/json'})
        with urllib.request.urlopen(call, timeout=180) as response:
            return json.load(response)
    session = post('/session', {'title': 'TinyAgent phone-local provider smoke'})
    print('Created diagnostic session:', session['id'], flush=True)
    response = post('/session/' + session['id'] + '/message', {
        'model': {'providerID': 'opencode', 'modelID': model},
        'parts': [{'type': 'text', 'text': 'Use the bash tool to run exactly: pwd; cat /etc/fedora-release . '
                  'The final period in this sentence is punctuation, not part of the command. '
                  'Do not modify files. Report the observed working directory and Fedora release, then write TINYAGENT_MODEL_OK.'}],
    })
    parts = response.get('parts', [])
    texts = [part.get('text', '') for part in parts if part.get('type') == 'text']
    tools = [part for part in parts if part.get('type') == 'tool']
    report = {'session': session['id'], 'model': 'opencode/' + model,
              'error': response.get('info', {}).get('error'), 'texts': texts,
              'tools': [{'tool': part.get('tool'), 'state': part.get('state')} for part in tools]}
    Path('/workspace/public-provider-smoke.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()

"""Check actual model/tool order against independently fetched phone files."""
import json
from pathlib import Path
import re
import sys

sid = sys.argv[1]
assert re.fullmatch(r'ses_[A-Za-z0-9]+', sid)
base = Path(__file__).resolve().parents[1] / 'evidence'
transcript = json.loads((base / (sid + '-probe.json')).read_text(encoding='utf-8'))
files = json.loads((base / (sid + '-files.json')).read_text(encoding='utf-8'))
assert transcript['status']['type'] == 'idle'
assert any(m['info'].get('modelID') == 'gpt-5.6-luna' and m['info'].get('providerID') == 'openai' for m in transcript['messages'])
assert not any(m['info'].get('error') for m in transcript['messages'])
tools = [p for m in transcript['messages'] for p in m['parts'] if p['type'] == 'tool']
assert all(p['state']['status'] == 'completed' for p in tools)
for r in range(1, 4):
    prefix = f'round-{r}/'
    before = files[prefix + 'before.log']['content']
    after = files[prefix + 'after.log']['content']
    assert 'AssertionError' in before and re.search(r'^exit_code=1$', before, re.M)
    assert after.strip() == 'exit_code=0'
    assert 'return a + b' in files[prefix + 'calculator.py']['content']
    test_path = f'/workspace/.tinyagent-qa/{sid}/{prefix}test_calculator.py'
    test_patches = [p['state']['input']['patchText'] for p in tools if p['tool'] == 'apply_patch' and test_path in p['state']['input']['patchText']]
    assert len(test_patches) == 1, 'Test changed after creation'
    original = test_patches[0].split('*** Add File: ' + test_path + '\n', 1)[1].split('*** ', 1)[0]
    original = '\n'.join(line[1:] for line in original.splitlines() if line.startswith('+'))
    assert original.strip() == files[prefix + 'test_calculator.py']['content'].strip()
    events = []
    for i, p in enumerate(tools):
        state, inp = p['state'], p['state']['input']
        if p['tool'] == 'bash' and inp.get('workdir', '').endswith('/' + prefix[:-1]):
            command = inp['command']
            if 'test_calculator.py > before.log' in command and 'status=$?' in command:
                events.append(('before', i))
            if 'test_calculator.py > after.log' in command and 'status=$?' in command:
                events.append(('after', i))
        if p['tool'] == 'apply_patch' and f'{prefix}calculator.py' in inp['patchText'] and '-    return a - b' in inp['patchText'] and '+    return a + b' in inp['patchText']:
            events.append(('fix', i))
    assert [kind for kind, _ in events] == ['before', 'fix', 'after'], events
    print(f'round={r} PASS real failure(1), source patch, unchanged test success(0)')
rounds = json.loads(files['result.json']['content'])['rounds']
assert [r['round'] for r in rounds] == [1, 2, 3]
for record in rounds:
    prefix = f"round-{record['round']}/"
    assert record['before_exit_code'] == 1 and record['after_exit_code'] == 0
    assert record['calculator_path'] == prefix + 'calculator.py'
    assert record['test_path'] == prefix + 'test_calculator.py'
    assert record['before_log_path'] == prefix + 'before.log'
    assert record['after_log_path'] == prefix + 'after.log'
print('PASS: 3 Fedora rounds using existing OAuth/Luna; not full release acceptance')

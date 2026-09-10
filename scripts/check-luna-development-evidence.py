"""Validate retained phone transcript and independently fetched fixture files."""
import json
from pathlib import Path
import re
import sys

sid = sys.argv[1]
assert re.fullmatch(r'ses_[A-Za-z0-9]+', sid)
base = Path(__file__).resolve().parents[1] / 'evidence'
transcript = json.loads((base / (sid + '-probe.json')).read_text(encoding='utf-8'))
files = json.loads((base / (sid + '-files.json')).read_text(encoding='utf-8'))
assert transcript['status']['type'] == 'idle', 'Model still running'
parts = [p for m in transcript['messages'] for p in m['parts']]
tools = [p for p in parts if p.get('type') == 'tool']
assert all(p['state']['status'] == 'completed' for p in tools)
assert 'return a + b' in files['calculator.py']['content']
assert re.search(r'FAILED \(failures=[1-9]\d*\)', files['before.log']['content'])
assert '1' in re.findall(r'exit_code\s*[:=]\s*(-?\d+)', files['before.log']['content'], re.I)
assert 'Ran 3 tests' in files['after.log']['content']
assert '\nOK\n' in files['after.log']['content']
codes = re.findall(r'exit_code\s*[:=]\s*(-?\d+)', files['after.log']['content'], re.I)
assert codes and all(code == '0' for code in codes)
patches = [p['state']['input']['patchText'] for p in tools if p.get('tool') == 'apply_patch']
test_patches = [p for p in patches if re.search(r'^\*\*\* (?:Add|Update|Delete) File: .*/test_calculator\.py$', p, re.M)]
assert len(test_patches) == 1, 'Tests changed after creation; inspect manually'
initial = test_patches[0].split('/test_calculator.py\n', 1)[1].split('*** ', 1)[0]
test_source = '\n'.join(line[1:] for line in initial.splitlines() if line.startswith('+'))
assert test_source.strip() == files['test_calculator.py']['content'].strip()
bash = [p['state'] for p in tools if p.get('tool') == 'bash']
assert any('unittest' in p['input']['command'] and '> before.log' in p['input']['command'] and '$?' in p['input']['command'] for p in bash)
assert any('unittest' in p['input']['command'] and '> after.log' in p['input']['command'] and '$?' in p['input']['command'] and p['metadata']['exit'] == 0 for p in bash)
assert any('py_compile' in p['input']['command'] and p['metadata']['exit'] == 0 for p in bash)
print('PASS: phone model repaired source, unchanged 3-test suite failed then passed; files independently fetched')

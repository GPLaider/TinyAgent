"""Phone-local package cancellation probe; refresh only, no RPM transaction."""
import importlib.util
import json
from pathlib import Path
import time
import uuid

spec = importlib.util.spec_from_file_location('client', '/root/.tinyagent/bootstrap/tinyagent-packages.py')
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)
name = Path('/root/.tinyagent/PACKAGE_SOCKET').read_text().strip()
job = str(uuid.uuid4())
path = '/packages/jobs/' + job
print('package_job_id=' + job, flush=True)
client.request(name, 'POST', '/packages/jobs', {'id': job, 'argv': ['repo', 'refresh']})
observed = {}
for _ in range(20):
    for process in Path('/proc').iterdir():
        if not process.name.isdecimal(): continue
        try:
            command = (process / 'cmdline').read_bytes().split(b'\0')[0]
            if command.rsplit(b'/', 1)[-1] == b'dnfast':
                observed[process.name] = (process / 'stat').read_text().rsplit(')', 1)[1].split()[19]
        except (OSError, IndexError): pass
    if observed: break
    time.sleep(0.05)
before = client.request(name, 'GET', path)
if before['status'] != 'running' or not observed:
    raise RuntimeError('Live dnfast process not observed; cancellation not exercised: ' + before['status'])
client.request(name, 'DELETE', path)
for _ in range(100):
    result = client.request(name, 'GET', path)
    if result['status'] not in ('running', 'cancel_requested'): break
    time.sleep(0.1)
assert result['status'] == 'cancelled', result
assert result['exit_code'] is not None, result
for pid, started in observed.items():
    try: current = Path('/proc', pid, 'stat').read_text().rsplit(')', 1)[1].split()[19]
    except (OSError, IndexError): current = None
    assert current != started, 'Original process remains alive: ' + pid
print(json.dumps({'job': job, 'observed_processes': observed, 'result': result, 'original_processes_gone': True}))

"""Phone-Fedora check; requires authorized Root and the installprobe fixture."""
import json, runpy, time, uuid
from pathlib import Path

client = runpy.run_path('/root/.tinyagent/bootstrap/tinyagent-packages.py')
request = client['request']
socket = Path('/root/.tinyagent/PACKAGE_SOCKET').read_text().strip()
records = []
def submit(command):
    identifier = str(uuid.uuid4())
    row = request(socket, 'POST', '/android/jobs', dict(id=identifier, mode='root', action='shell', cwd='/', command=command))
    print('accepted='+identifier, flush=True)
    return identifier
def wait(identifier, target=None):
    deadline=time.monotonic()+90
    while time.monotonic()<deadline:
        row=request(socket, 'GET', '/android/jobs/'+identifier)
        if target and row['status']==target:return row
        if row['status'] not in ('queued','starting','checking','running','cancel_requested'):return row
        time.sleep(.3)
    raise AssertionError(row)

first=submit('sleep 8')
assert wait(first,'running')['status']=='running'
second=submit('pm path io.github.gplaider.tinyagent.installprobe')
third=submit('exit 99')
assert request(socket,'GET','/android/jobs/'+second)['status']=='queued'
request(socket,'DELETE','/android/jobs/'+third)
for identifier in (first,second,third):
    records.append(wait(identifier))
assert records[0]['status']=='completed' and records[0]['exit_code']==0,records
assert records[1]['status']=='completed' and 'package:' in records[1]['stdout'],records
assert records[2]['status']=='cancelled' and records[2]['exit_code'] is None,records
for unused in range(6):
    row=wait(submit('id'))
    assert row['status']=='completed' and row['exit_code']==0 and row['execution_uid']==0,row
    records.append(row)
try:
    request(socket,'GET','/android/jobs/'+str(uuid.uuid4()))
    raise AssertionError('missing ID accepted')
except client['BridgeResponseError'] as error:
    assert 'Unknown Android job ID' in str(error) and '/data/user/' not in str(error),str(error)
Path('/shared/android-fifo-result.json').write_text(json.dumps(records,indent=2))
print(json.dumps(dict(passed=True, jobs=records)),flush=True)

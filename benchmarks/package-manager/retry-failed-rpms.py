"""One scoped retry of the two failed RPMs, preserving diagnostics before mutation."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

assert os.environ.get('TINYAGENT_EXECUTION_PROVIDER') == 'fedora-local'
base = Path('/workspace/tinyagent-six-builds')
state = json.loads((base/'rpm-failure-state.json').read_text())
record = {'rpms': [], 'before': {}}
with (base/'.native-preparation.lock').open('a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    for filename in state['cached_rpms']:
        path = Path(filename)
        assert path.is_relative_to('/var/cache') and path.name.startswith(('ncurses-devel-', 'perl-Module-CoreList-tools-'))
        with path.open('rb') as stream: checksum = hashlib.file_digest(stream, 'sha256').hexdigest()
        info = subprocess.run(['rpm', '-qp', '--dump', str(path)], capture_output=True, text=True)
        record['rpms'].append(dict(path=filename, sha256=checksum, dump=info.stdout, exit=info.returncode))
    for path in [Path('/usr/bin/corelist'), Path('/usr/lib64/libtic.so')]:
        record['before'][str(path)] = dict(exists=path.exists(), symlink=path.is_symlink(),
                                         target=os.readlink(path) if path.is_symlink() else None)
    run = base/('rpm-retry-'+str(time.time_ns()))
    run.mkdir()
    (run/'before.json').write_text(json.dumps(record, indent=2)+'\n')
    command = ['microdnf', 'install', '-y', 'ncurses-devel', 'perl-Module-CoreList-tools']
    print('RPM_RETRY', run, flush=True)
    began = time.monotonic()
    with (run/'install.log').open('w') as log:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            log.write(line); log.flush(); print(line, end='', flush=True)
        code = process.wait()
    report = dict(command=command, exit_code=code, seconds=time.monotonic()-began)
    check = subprocess.run(['rpm', '-q', 'ncurses-devel', 'perl-Module-CoreList-tools'], capture_output=True, text=True)
    report.update(query_exit=check.returncode, packages=check.stdout+check.stderr)
    (run/'result.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report), flush=True)
    raise SystemExit(code or check.returncode)

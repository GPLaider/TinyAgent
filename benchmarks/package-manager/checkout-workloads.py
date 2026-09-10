"""Run in the phone Fedora. Pin source inputs before deriving ARM build recipes."""
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

assert os.environ.get('TINYAGENT_EXECUTION_PROVIDER') == 'fedora-local'
assert os.uname().machine == 'aarch64'
base = Path('/workspace/tinyagent-six-builds')
base.mkdir(exist_ok=True)
manifest = json.loads(Path('/shared/workloads.json').read_text())
assert len(manifest['workloads']) == 6
with (base / '.checkout.lock').open('a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    reports = []
    for workload in manifest['workloads']:
        name = workload['name'].lower().replace(' ', '-')
        assert name.replace('-', '').isalnum()
        revision = workload['commit']
        assert len(revision) == 40 and all(c in '0123456789abcdef' for c in revision)
        assert workload['url'].startswith(('https://github.com/', 'https://code.videolan.org/'))
        target = base / name
        began = time.monotonic()
        report = dict(name=name, commit=revision, url=workload['url'], stage='checkout', status='running')
        reports.append(report)
        def save():
            (base / 'checkout-results.json').write_text(json.dumps(reports, indent=2) + '\n')
        save()
        print('CHECKOUT', name, revision, flush=True)
        try:
            assert shutil.disk_usage(base).free > 20 * 1024**3, 'Less than 20 GiB free'
            with (base / (name + '-checkout.log')).open('ab') as log:
                def git(*args):
                    result = subprocess.run(['git', *args], cwd=base, stdout=log, stderr=subprocess.STDOUT, timeout=900)
                    if result.returncode:
                        raise RuntimeError('git exit=' + str(result.returncode) + '; inspect checkout log')
                if not target.exists():
                    git('init', str(target))
                    git('-C', str(target), 'remote', 'add', 'origin', workload['url'])
                    git('-C', str(target), 'fetch', '--depth=1', 'origin', revision)
                    git('-C', str(target), 'checkout', '--detach', revision)
                actual = subprocess.check_output(['git', '-C', str(target), 'rev-parse', 'HEAD']).decode().strip()
                assert actual == revision, 'Existing checkout differs; retained for inspection'
            report['status'] = 'passed'
            report['submodules'] = subprocess.check_output(['git', '-C', str(target), 'submodule', 'status']).decode()
            report['scope'] = 'Pinned parent checkout only; submodules and build toolchains pending'
        except Exception as error:
            report['status'] = 'failed'
            report['error'] = str(error)
        report['seconds'] = round(time.monotonic() - began, 3)
        save()
        print(json.dumps(report), flush=True)
    print('checkout_complete passed=' + str(sum(r['status'] == 'passed' for r in reports)), flush=True)
    raise SystemExit(0 if all(r['status'] == 'passed' for r in reports) else 1)

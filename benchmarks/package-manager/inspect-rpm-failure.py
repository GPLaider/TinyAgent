"""Retain RPM state and probe only newly created files in the affected directories."""
import json
import os
from pathlib import Path
import subprocess
import uuid

assert os.environ.get('TINYAGENT_EXECUTION_PROVIDER') == 'fedora-local'
report = {'commands': [], 'filesystem': []}
for command in [
    ['rpm', '-q', 'perl-Module-CoreList-tools', 'ncurses-devel', 'rustup', 'which'],
    ['rpm', '--eval', '%{__transaction_selinux}'],
    ['rpm', '-q', 'rpm-plugin-selinux'],
    ['selinuxenabled'],
    ['microdnf', 'history', 'info', 'last'],
]:
    result = subprocess.run(command, capture_output=True, text=True)
    report['commands'].append(dict(command=command, exit=result.returncode, output=result.stdout+result.stderr))
for parent in [Path('/usr/bin'), Path('/usr/lib64')]:
    directory = parent/('.tinyagent-probe-'+uuid.uuid4().hex)
    directory.mkdir()
    try:
        (directory/'file').write_text('owned probe\n')
        for action in ['symlink', 'link']:
            try:
                if action == 'symlink': os.symlink('file', directory/action)
                else: os.link(directory/'file', directory/action)
                report['filesystem'].append(dict(parent=str(parent), action=action, result='passed'))
            except OSError as error:
                report['filesystem'].append(dict(parent=str(parent), action=action, errno=error.errno, error=str(error)))
    finally:
        for path in directory.iterdir(): path.unlink()
        directory.rmdir()
report['cached_rpms'] = [str(p) for p in Path('/var/cache').rglob('*.rpm')
                          if p.name.startswith(('ncurses-devel-', 'perl-Module-CoreList-tools-'))]
path = Path('/workspace/tinyagent-six-builds/rpm-failure-state.json')
path.write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report), flush=True)

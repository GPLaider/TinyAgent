"""Verify the final ARM candidate in the real app guest; no RPM installation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tarfile
import time

variants = {
    'verity': ('4717e117b735ea80ee2f1438a5fab1893263134d', '30a00ca185aa43162d395e2cfee47e7374e7f36d66d79915f7c9c279e2f103ad'),
    'loader': ('e7d803025137de3f9b869e110184c417b0b3e0b8', 'e6f409d07ae9e08fad4a546e16aed141dfe5a3d00bd631280a175d9595db6555'),
    'direct': ('e7d803025137de3f9b869e110184c417b0b3e0b8', '79ecd25a4c35cf99015ec81d8a65810a374cb701e9bffbfb14d3808c502d46a8'),
    'diagnostic': ('206cfc7a2556153317ec639d2da1b6a9d168e1d3', 'f68560d31fab82ede4bf7e9f6b99e1fa9232f330d49db01f002a32c38a50dbc4'),
    'rename': ('03d6430de08a3dc56c1519b60aa5546c76999e8c', 'ce1ec6b1f0a4b26969a89829e30cd6797f5f71fd24a32abbc0ef8d9f3bf363d1'),
    'eacces': ('5313ef65d64d46969bac9198debd4b422c3aefc2', '2c15be4b9515406ba0c04b846d1692c3c9f77479eec2bc99333f696391b5c503'),
}
parser = argparse.ArgumentParser()
group = parser.add_mutually_exclusive_group()
for variant in variants:
    group.add_argument('--' + variant, dest='variant', action='store_const', const=variant)
parser.set_defaults(variant='loader')
parser.add_argument('--background', action='store_true')
args = parser.parse_args()
commit, expected_archive = variants[args.variant]
direct = args.variant != 'loader'
revision = commit[:7]
root = Path('/workspace/tinyagent-package-bench-20260909') / ('fixed-' + revision + ('-direct' if direct else ''))
root.mkdir(exist_ok=True)
if args.background:
    with (root / 'worker.log').open('x') as log:
        p = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--' + args.variant],
                             stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                             start_new_session=True)
    (root / 'worker.pid').write_text(str(p.pid))
    print('worker_pid=' + str(p.pid))
    sys.exit(0)

def save(value):
    (root / 'result.json').write_text(json.dumps(value, indent=2))
    print(json.dumps(value), flush=True)

report = {'commit': commit, 'phase': 'verify'}
try:
    identity = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines()
                    if line.startswith(('Uid:', 'Gid:', 'CapEff:', 'Seccomp:')))
    assert int(identity['Uid'].split()[0]) >= 10000
    assert int(identity['CapEff'].strip(), 16) == 0
    report['identity'] = identity
    archive = root / 'bundle.tar.gz'
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    assert digest == expected_archive
    report['archive_sha256'] = digest
    with tarfile.open(archive) as source:
        source.extractall(root, filter='data')
    bundle = root / 'dnfast'
    manifest = json.loads((bundle / 'manifest.json').read_text())
    for relative, expected in manifest['files'].items():
        path = (bundle / relative).resolve()
        assert path.is_relative_to(bundle.resolve())
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, relative
    report['verified_files'] = len(manifest['files'])
    report['dnf_conf'] = Path('/etc/dnf/dnf.conf').read_text()
    command = ([str(bundle / 'bin/dnfast')] if direct else
               [str(bundle / 'lib/ld-linux-aarch64.so.1'), '--library-path', str(bundle / 'lib'), str(bundle / 'bin/dnfast')])
    command += ['repo', 'makecache', '--repo', 'fedora']
    report.update(phase='refresh', command=command)
    save(report)
    started = time.monotonic()
    with (root / 'makecache.log').open('w') as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                   start_new_session=True, env={**os.environ, 'LC_ALL': 'C'})
        report['pid'] = process.pid
        save(report)
        try:
            process.wait(timeout=600)
        except subprocess.TimeoutExpired:
            report['timeout'] = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
    report.update(phase='complete', exit=process.returncode, seconds=time.monotonic() - started,
                  log_tail=(root / 'makecache.log').read_text(errors='replace')[-6000:])
    save(report)
except Exception as error:
    report.update(phase='failed', error=str(error))
    save(report)
    raise

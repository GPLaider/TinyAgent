"""Read-only toolchain inventory and child-only namespace capability probe."""
import ctypes
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess

root = Path('/workspace/tinyagent-package-bench-20260909')
root.mkdir(exist_ok=True)
status = Path('/proc/self/status').read_text()
identity = {line.split(':', 1)[0]: line.split(':', 1)[1].strip()
            for line in status.splitlines()
            if line.split(':', 1)[0] in {'Uid', 'Gid', 'CapEff', 'Seccomp', 'NoNewPrivs'}}
assert int(identity['Uid'].split()[0]) >= 10000, 'Must execute inside Android app UID'
assert int(identity['CapEff'], 16) == 0, 'Benchmark must not use host root capabilities'
pid = os.fork()
if pid == 0:
    libc = ctypes.CDLL(None, use_errno=True)
    before = os.readlink('/proc/self/ns/mnt')
    result = libc.unshare(0x00020000)  # CLONE_NEWNS; child exits without mounting anything.
    error = ctypes.get_errno() if result else 0
    after = os.readlink('/proc/self/ns/mnt')
    (root / 'namespace-probe.json').write_text(json.dumps(
        {'operation': 'unshare(CLONE_NEWNS)', 'result': result,
         'errno': error, 'message': os.strerror(error) if error else 'success',
         'namespace_before': before, 'namespace_after': after,
         'namespace_changed': before != after}))
    os._exit(0)
_, exit_status = os.waitpid(pid, 0)
assert os.waitstatus_to_exitcode(exit_status) == 0
tools = {}
for name, args in [('java', ['-version']), ('git', ['--version']), ('go', ['version']),
                   ('clang', ['--version']), ('cmake', ['--version']), ('ninja', ['--version']),
                   ('rustc', ['--version']), ('cargo', ['--version']),
                   ('autoconf', ['--version']), ('automake', ['--version'])]:
    path = shutil.which(name)
    if not path:
        tools[name] = {'available': False}
        continue
    try:
        p = subprocess.run([path, *args], capture_output=True, text=True, timeout=20)
        tools[name] = {'path': path, 'exit': p.returncode,
                       'output': (p.stdout + p.stderr)[:1500]}
    except subprocess.TimeoutExpired:
        tools[name] = {'path': path, 'timeout': True}
report = {'machine': platform.machine(), 'kernel': platform.release(), 'identity': identity,
          'namespace': json.loads((root / 'namespace-probe.json').read_text()),
          'tools': tools, 'free_bytes': shutil.disk_usage(root).free}
(root / 'stock-preflight.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report))

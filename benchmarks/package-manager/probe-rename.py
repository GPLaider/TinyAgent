"""Test named-file publication primitives, not a production cache implementation."""
import ctypes
import json
import os
from pathlib import Path
import tempfile

status = Path('/proc/self/status').read_text()
identity = dict(line.split(':', 1) for line in status.splitlines() if line.startswith(('Uid:', 'CapEff:')))
assert int(identity['Uid'].split()[0]) >= 10000 and int(identity['CapEff'], 16) == 0
report = {'identity': identity}
libc = ctypes.CDLL(None, use_errno=True)
libc.renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
libc.renameat2.restype = ctypes.c_int
with tempfile.TemporaryDirectory(prefix='tinyagent-rename-', dir='/var/cache/dnfast/solv-v1') as temporary:
    root = Path(temporary)
    directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    fd = os.open('staging', os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
    try:
        os.write(fd, b'candidate')
        os.fsync(fd)
        (root / 'winner').write_bytes(b'existing-winner')
        ctypes.set_errno(0)
        code = libc.renameat2(directory, b'staging', directory, b'winner', 1)
        report['existing_target'] = {'result': code, 'errno': ctypes.get_errno() if code else 0,
                                     'winner_preserved': (root / 'winner').read_bytes() == b'existing-winner'}
        ctypes.set_errno(0)
        code = libc.renameat2(directory, b'staging', directory, b'published', 1)
        report['new_target'] = {'result': code, 'errno': ctypes.get_errno() if code else 0}
        if code == 0:
            reopened = os.open('published', os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
            try:
                before, after = os.fstat(fd), os.fstat(reopened)
                report['new_target'].update(same_inode=(before.st_dev, before.st_ino) == (after.st_dev, after.st_ino),
                                            bytes_match=os.read(reopened, 100) == b'candidate',
                                            target_is_symlink=(root / 'published').is_symlink())
            finally:
                os.close(reopened)
        os.fsync(directory)
        report['directory_fsync'] = True
    finally:
        os.close(fd)
        os.close(directory)
Path('/workspace/tinyagent-package-bench-20260909/rename-probe.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report))

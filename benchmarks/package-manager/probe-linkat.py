"""Probe anonymous-file publication in app-owned cache; never touches RPMDB."""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import platform
import tempfile

root = Path('/workspace/tinyagent-package-bench-20260909')
identity = {line.split(':', 1)[0]: line.split(':', 1)[1].strip()
            for line in Path('/proc/self/status').read_text().splitlines()
            if line.startswith(('Uid:', 'CapEff:', 'Seccomp:'))}
assert int(identity['Uid'].split()[0]) >= 10000
assert int(identity['CapEff'], 16) == 0
report = {'identity': identity, 'kernel': platform.release(), 'probes': []}
libc = ctypes.CDLL(None, use_errno=True)
libc.linkat.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
libc.linkat.restype = ctypes.c_int
with tempfile.TemporaryDirectory(prefix='tinyagent-linkat-', dir='/var/cache/dnfast/solv-v1') as directory:
    directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        fd = os.open(directory, os.O_TMPFILE | os.O_RDWR | os.O_CLOEXEC, 0o600)
        try:
            os.write(fd, b'tinyagent-linkat-probe\n')
            os.fsync(fd)
            for label, source_fd, source, flags in [
                ('AT_EMPTY_PATH', fd, b'', 0x1000),
                ('procfd-AT_SYMLINK_FOLLOW', -100, f'/proc/self/fd/{fd}'.encode(), 0x400),
            ]:
                target = label.encode()
                ctypes.set_errno(0)
                result = libc.linkat(source_fd, source, directory_fd, target, flags)
                error = ctypes.get_errno() if result != 0 else 0
                row = {'operation': label, 'flags': flags, 'result': result,
                       'errno': error, 'message': os.strerror(error) if error else 'success'}
                if result == 0:
                    actual, expected = os.stat(target, dir_fd=directory_fd), os.fstat(fd)
                    row['same_inode'] = (actual.st_dev, actual.st_ino) == (expected.st_dev, expected.st_ino)
                    row['sha256'] = hashlib.sha256((Path(directory) / label).read_bytes()).hexdigest()
                report['probes'].append(row)
        finally:
            os.close(fd)
    except OSError as error:
        report['open_tmpfile_error'] = {'errno': error.errno, 'message': str(error)}
    finally:
        os.close(directory_fd)
(root / 'linkat-probe.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report))

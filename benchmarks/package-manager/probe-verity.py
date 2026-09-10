"""Match dnfast's fs-verity enable ioctl on a disposable app-owned file."""
import fcntl
import json
import os
from pathlib import Path
import struct
import tempfile

identity = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines()
                if line.startswith(('Uid:', 'CapEff:')))
assert int(identity['Uid'].split()[0]) >= 10000 and int(identity['CapEff'], 16) == 0
report = {'identity': identity, 'ioctl': 'FS_IOC_ENABLE_VERITY', 'request': '0x40806685',
          'version': 1, 'hash_algorithm': 1}
with tempfile.TemporaryDirectory(prefix='tinyagent-verity-', dir='/var/cache/dnfast/solv-v1') as directory:
    path = Path(directory) / 'content'
    with path.open('xb') as output:
        output.write(b'tinyagent-verity-probe\n')
        output.flush()
        os.fsync(output.fileno())
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        argument = struct.pack('=II', 1, 1) + bytes(120)
        assert len(argument) == 128
        try:
            fcntl.ioctl(fd, 0x40806685, argument)
            report.update(result=0, errno=0)
        except OSError as error:
            report.update(result=-1, errno=error.errno, message=str(error))
        # _IOWR('f', 134, struct fsverity_digest): four-byte header, then digest buffer.
        measurement = bytearray(struct.pack('=HH', 1, 32) + bytes(32))
        try:
            fcntl.ioctl(fd, 0xC0046686, measurement, True)
            algorithm, size = struct.unpack('=HH', measurement[:4])
            report['measure'] = {'result': 0, 'errno': 0, 'algorithm': algorithm, 'size': size,
                                 'digest': measurement[4:4 + min(size, 32)].hex()}
        except OSError as error:
            report['measure'] = {'result': -1, 'errno': error.errno, 'message': str(error)}
        report['content_readable_and_unchanged'] = os.read(fd, 100) == b'tinyagent-verity-probe\n'
    finally:
        os.close(fd)
Path('/workspace/tinyagent-package-bench-20260909/verity-probe.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report))

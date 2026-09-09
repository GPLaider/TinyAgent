"""Reuse identical ZIP payloads; reconstruct the exact signed APK, never re-sign it."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import struct
import zipfile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def payloads(path, data):
    with zipfile.ZipFile(path) as archive:
        for entry in sorted(archive.infolist(), key=lambda entry: entry.header_offset):
            offset = entry.header_offset
            assert data[offset:offset + 4] == b'PK\x03\x04'
            name, extra = struct.unpack_from('<HH', data, offset + 26)
            start = offset + 30 + name + extra
            yield entry.filename, start, entry.compress_size


def create(old_path, new_path, patch_path):
    old, new = old_path.read_bytes(), new_path.read_bytes()
    previous = {name: (start, size) for name, start, size in payloads(old_path, old)}
    spans, cursor = [], 0
    for name, start, size in payloads(new_path, new):
        source, length = previous.get(name, (-1, -1))
        if size < 4096 or size != length or old[source:source + size] != new[start:start + size]:
            continue
        if start > cursor:
            spans.append(base64.b64encode(new[cursor:start]).decode('ascii'))
        spans.append([source, size])
        cursor = start + size
    spans.append(base64.b64encode(new[cursor:]).decode('ascii'))
    patch_path.write_text(json.dumps({'old': digest(old), 'new': digest(new), 'size': len(new), 'spans': spans}), encoding='utf-8')
    print(f'patch_bytes={patch_path.stat().st_size} apk_bytes={len(new)} sha256={digest(new)}')


def apply(old_path, patch_path, output):
    old = old_path.read_bytes()
    plan = json.loads(patch_path.read_text(encoding='utf-8'))
    assert digest(old) == plan['old'], 'Base APK differs'
    assert not output.exists(), 'Refusing to replace an existing APK'
    temporary = output.with_name(output.name + '.part')
    written, checksum = 0, hashlib.sha256()
    with temporary.open('xb') as stream:
        try:
            for span in plan['spans']:
                if isinstance(span, list):
                    start, size = span
                    assert isinstance(start, int) and isinstance(size, int) and 0 <= start <= len(old) and 0 <= size <= len(old) - start
                    data = old[start:start + size]
                else:
                    data = base64.b64decode(span, validate=True)
                written += len(data)
                assert written <= plan['size']
                checksum.update(data)
                stream.write(data)
            assert written == plan['size'] and checksum.hexdigest() == plan['new'], 'Reconstructed APK differs'
            stream.flush()
            os.fsync(stream.fileno())
        except BaseException:
            stream.close()
            temporary.unlink()
            raise
    os.replace(temporary, output)
    print(f'verified_bytes={written} sha256={checksum.hexdigest()}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['create', 'apply'])
    parser.add_argument('paths', nargs=3, type=Path)
    args = parser.parse_args()
    (create if args.operation == 'create' else apply)(*args.paths)

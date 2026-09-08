"""Lossless APK transfer with source/target hash checks. Building is a separate operation."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import zipfile

def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def spans(path):
    with zipfile.ZipFile(path) as archive, path.open('rb') as stream:
        cuts = {0, path.stat().st_size, archive.start_dir}
        for entry in archive.infolist():
            stream.seek(entry.header_offset + 26)
            name, extra = struct.unpack('<HH', stream.read(4))
            data = entry.header_offset + 30 + name + extra
            cuts.update((entry.header_offset, data, data + entry.compress_size))
        ordered = sorted(cuts)
        for start, end in zip(ordered, ordered[1:]):
            stream.seek(start)
            chunk = stream.read(end-start)
            yield start, chunk

def create(old, new, patch):
    known = {hashlib.sha256(chunk).hexdigest(): (offset, len(chunk)) for offset, chunk in spans(old)}
    plan = dict(old_sha256=digest(old), new_sha256=digest(new), size=new.stat().st_size, segments=[])
    with zipfile.ZipFile(patch, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for index, (_, chunk) in enumerate(spans(new)):
            key = hashlib.sha256(chunk).hexdigest()
            if key in known:
                offset, size = known[key]
                plan['segments'].append(dict(offset=offset, size=size))
            else:
                name = str(index)
                archive.writestr(name, chunk)
                plan['segments'].append(dict(file=name, size=len(chunk)))
        archive.writestr('plan.json', json.dumps(plan))
    print(json.dumps(dict(patch_bytes=patch.stat().st_size, target_bytes=plan['size'], target_sha256=plan['new_sha256'])))

def apply(old, patch, target):
    assert old.resolve() != target.resolve() and patch.resolve() != target.resolve()
    with zipfile.ZipFile(patch) as archive:
        plan = json.loads(archive.read('plan.json'))
        assert digest(old) == plan['old_sha256'], 'Installed APK differs from delta source'
        assert 0 < plan['size'] <= 1024**3
        assert sum(part['size'] for part in plan['segments']) == plan['size']
        with old.open('rb') as source, target.open('xb') as output:
            for part in plan['segments']:
                assert 0 <= part['size'] <= plan['size']
                if 'offset' in part:
                    assert 0 <= part['offset'] <= old.stat().st_size - part['size']
                    source.seek(part['offset'])
                    remaining = part['size']
                    while remaining:
                        chunk = source.read(min(65536, remaining))
                        assert chunk
                        output.write(chunk); remaining -= len(chunk)
                else:
                    chunk = archive.read(part['file'])
                    assert len(chunk) == part['size']
                    output.write(chunk)
        assert digest(target) == plan['new_sha256'], 'Reconstructed APK hash mismatch; do not install'
    print('Verified reconstructed APK:', plan['new_sha256'])

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['create', 'apply'])
    parser.add_argument('old', type=Path)
    parser.add_argument('second', type=Path)
    parser.add_argument('third', type=Path)
    args = parser.parse_args()
    (create if args.mode == 'create' else apply)(args.old, args.second, args.third)

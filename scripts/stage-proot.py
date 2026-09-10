"""Stage pinned Termux dependencies and the source-built TinyAgent PRoot.

Repository hashes are checked over HTTPS or verified local cache. Dependency
source rebuild and repository signature checking remain separate gates.
"""
import hashlib
import io
import json
from pathlib import Path
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://packages.termux.dev/apt/termux-main/'
PACKAGES = {'proot', 'libtalloc', 'libandroid-shmem'}


def fetch(url, limit=16 * 1024 * 1024):
    with urllib.request.urlopen(url, timeout=45) as response:
        data = response.read(limit + 1)
    assert len(data) <= limit, 'Download exceeds staging limit'
    return data


def ar_members(data):
    assert data[:8] == b'!<arch>\n'
    offset = 8
    while offset < len(data):
        header = data[offset:offset+60]
        assert len(header) == 60 and header[58:] == b'`\n'
        size = int(header[48:58])
        offset += 60
        assert 0 <= size <= len(data)-offset
        yield header[:16].decode().strip().rstrip('/'), data[offset:offset+size]
        offset += size + size % 2


def main():
    dest = ROOT / 'app/src/main/jniLibs/arm64-v8a'
    dest.mkdir(parents=True, exist_ok=True)
    cache = ROOT / '.checks/proot-packages'
    cache.mkdir(parents=True, exist_ok=True)
    pins = json.loads((ROOT / 'evidence/proot-staging.json').read_text())
    records = []
    outputs = {}
    for fields in pins['packages']:
        name = fields['Package']
        relative = fields['Filename']
        assert not relative.startswith('/') and '..' not in relative.split('/')
        cached = cache / Path(relative).name
        data = cached.read_bytes() if cached.is_file() else fetch(BASE + relative)
        assert hashlib.sha256(data).hexdigest() == fields['SHA256']
        (cache / Path(relative).name).write_bytes(data)
        records.append({k: fields[k] for k in ['Package', 'Version', 'Filename', 'SHA256']})
        payload = next(content for member, content in ar_members(data) if member.startswith('data.tar.'))
        with tarfile.open(fileobj=io.BytesIO(payload)) as archive:
            for member in archive:
                if not member.isfile():
                    continue
                basename = Path(member.name).name
                target = None
                if member.name.endswith('/bin/proot'): target = 'libproot.so'
                if member.name.endswith('/libexec/proot/loader'): target = 'libproot_loader.so'
                if basename.startswith('libtalloc.so.'): target = 'libtalloc.so'
                if basename == 'libandroid-shmem.so': target = basename
                if target:
                    content = archive.extractfile(member).read()
                    assert content[:4] == b'\x7fELF'
                    # Android extracts lib*.so only. Keep ELF string offsets intact.
                    content = content.replace(b'libtalloc.so.2\0', b'libtalloc.so\0\0\0')
                    (dest / target).write_bytes(content)
                    outputs[target] = hashlib.sha256(content).hexdigest()
    assert {r['Package'] for r in records} == PACKAGES
    assert set(outputs) == {'libproot.so', 'libproot_loader.so', 'libtalloc.so', 'libandroid-shmem.so'}
    assert outputs == pins['output_sha256'], 'Packaged native bytes differ from source pins'
    # Preserve dependency provenance while promoting the separately source-built tracer.
    candidate = json.loads((ROOT / 'runtime/proot-exitkill-1.json').read_text())
    archive_path = ROOT / 'runtime/proot-exitkill-1.tar.gz'
    assert candidate['archive'] == archive_path.name
    assert hashlib.sha256(archive_path.read_bytes()).hexdigest() == candidate['archive_sha256']
    assert candidate['patch_sha256'] == hashlib.sha256((ROOT / 'patches/proot-exitkill.patch').read_bytes()).hexdigest()
    assert set(candidate['outputs']) == {'libproot.so', 'libproot_loader.so'}
    for name, digest in candidate['dependencies'].items():
        assert outputs[name] == digest
    replacements = {}
    with tarfile.open(archive_path) as archive:
        members = archive.getmembers()
        assert len(members) == 2 and {m.name for m in members} == set(candidate['outputs'])
        for member in members:
            assert member.isfile() and member.size < 1024 * 1024
            data = archive.extractfile(member).read()
            assert hashlib.sha256(data).hexdigest() == candidate['outputs'][member.name]
            replacements[member.name] = data
    for name, data in replacements.items():
        (dest / name).write_bytes(data)
        outputs[name] = hashlib.sha256(data).hexdigest()
    print('Source-built PRoot promoted: ' + json.dumps(outputs, sort_keys=True))
    print(json.dumps(pins, indent=2))


if __name__ == '__main__':
    main()

"""Pinned SDK inputs for the phone build. ARM64 tools are third-party rebuilds, not Google binaries."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tarfile
import tempfile
import urllib.request
import zipfile

pins = [
    ('arm64.tar.xz', 'https://github.com/HomuHomu833/android-sdk-custom/releases/download/37.0.0/android-sdk-aarch64-linux-musl.tar.xz', 'sha256', 'b904edf8cf20c233de9d884a2da4a8e7eadea4d23aa10859abb9466660f3e803', 159016720),
    ('platform.zip', 'https://dl.google.com/android/repository/platform-36_r02.zip', 'sha1', '2c1a80dd4d9f7d0e6dd336ec603d9b5c55a6f576', 65878410),
    ('build-tools.zip', 'https://dl.google.com/android/repository/build-tools_r35_linux.zip', 'sha1', '2cfaa0bbb2336e9ec18ed3ecea84fa2e2af607bc', 61958799),
]

def download(url, target, algorithm, expected, size):
    if not target.exists():
        print('Downloading', target.name, size, flush=True)
        part = target.with_name(target.name + '.part')
        with urllib.request.urlopen(url, timeout=60) as source, part.open('wb') as output:
            total = 0
            while chunk := source.read(65536):
                total += len(chunk)
                assert total <= size
                output.write(chunk)
        assert part.stat().st_size == size
        with part.open('rb') as stream: assert hashlib.file_digest(stream, algorithm).hexdigest() == expected
        part.replace(target)
    assert target.stat().st_size == size
    with target.open('rb') as stream: assert hashlib.file_digest(stream, algorithm).hexdigest() == expected

def unpack(target, dest):
    if dest.exists(): return
    stage = Path(tempfile.mkdtemp(prefix=target.name + '.unpacking-', dir=dest.parent))
    try:
        if target.name.endswith('.xz'):
            with tarfile.open(target) as archive: archive.extractall(stage, filter='data')
        else:
            with zipfile.ZipFile(target) as archive:
                for entry in archive.infolist():
                    assert not entry.filename.startswith('/') and '..' not in Path(entry.filename).parts
                    path = Path(archive.extract(entry, stage))
                    if path.is_file(): path.chmod(0o755 if (entry.external_attr >> 16) & 0o111 else 0o644)
        stage.replace(dest)
    finally:
        if stage.exists(): shutil.rmtree(stage)

def main():
    import fcntl
    assert os.environ.get('TINYAGENT_EXECUTION_PROVIDER') == 'fedora-local'
    assert os.uname().machine == 'aarch64'
    base = Path('/opt/tinyagent-build/sdk-inputs')
    base.mkdir(parents=True, exist_ok=True)
    with (base / '.prepare.lock').open('a') as lock:
        print('Waiting for SDK preparation lock', flush=True)
        fcntl.flock(lock, fcntl.LOCK_EX)
        report = []
        for name, url, algorithm, expected, size in pins:
            target = base / name
            download(url, target, algorithm, expected, size)
            with target.open('rb') as stream: sha256 = hashlib.file_digest(stream, 'sha256').hexdigest()
            report.append(dict(url=url, size=size, sha256=sha256))
            dest = base / (name + '.unpacked')
            unpack(target, dest)
            print('Verified and extracted', name, flush=True)
            print('Roots:', ', '.join(p.name for p in dest.iterdir()), flush=True)
        (base / 'provenance.json').write_text(json.dumps(report, indent=2)+'\n')
    print('sdk_inputs_exit=0', flush=True)

def self_check():
    import io
    from unittest.mock import patch
    class Interrupted(io.BytesIO):
        def read(self, size=-1):
            if self.tell(): raise OSError('simulated interruption')
            return super().read(1)
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        target = base / 'input.zip'
        with patch('urllib.request.urlopen', return_value=Interrupted(b'ok')):
            try: download('https://example.invalid/', target, 'sha256', hashlib.sha256(b'ok').hexdigest(), 2)
            except OSError: pass
            else: raise AssertionError('Interrupted download accepted')
        assert not target.exists()
        with patch('urllib.request.urlopen', return_value=io.BytesIO(b'ok')):
            download('https://example.invalid/', target, 'sha256', hashlib.sha256(b'ok').hexdigest(), 2)
        assert target.read_bytes() == b'ok' and not target.with_name('input.zip.part').exists()
        with zipfile.ZipFile(target, 'w') as archive: archive.writestr('../escape', b'no')
        dest = base / 'unpacked'
        try: unpack(target, dest)
        except AssertionError: pass
        else: raise AssertionError('Archive traversal accepted')
        assert not dest.exists() and not list(base.glob('*.unpacking-*'))
        with zipfile.ZipFile(target, 'w') as archive: archive.writestr('sdk/test', b'ok')
        unpack(target, dest)
        assert (dest / 'sdk/test').read_bytes() == b'ok'
    print('SDK self-check passed: interrupted download recovery, rejected traversal, atomic extraction')

if __name__ == '__main__':
    self_check() if sys.argv[1:] == ['--self-check'] else main()

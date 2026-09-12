"""Linux check: root lock, preserved state, interrupted publication and retry."""
import fcntl
from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import zipfile

spec = importlib.util.spec_from_file_location('upgrade', Path(__file__).with_name('upgrade-dnfast-empty.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
old = {'usr/bin/dnfast': b'old-cli', 'usr/libexec/dnfast-executor': b'old-executor'}
new = {key: b'new-' + value for key, value in old.items()}
new['opt/tinyagent-dnfast/test/lib/runtime.so'] = b'new-library'
module.OLD = {name: module.digest(data) for name, data in old.items()}
buffer = io.BytesIO()
with tarfile.open(fileobj=buffer, mode='w:gz') as archive:
    for name, data in new.items():
        entry = tarfile.TarInfo(name)
        entry.size = len(data)
        archive.addfile(entry, io.BytesIO(data))
overlay = buffer.getvalue()
manifest = json.dumps({'overlay_sha256': module.digest(overlay), 'files': {n: module.digest(d) for n, d in new.items()}}).encode()
module.MANIFEST = module.digest(manifest)
identity = 'a' * 64
with tempfile.TemporaryDirectory() as temporary:
    base = Path(temporary)
    apk = base / 'test.apk'
    with zipfile.ZipFile(apk, 'w') as archive:
        archive.writestr('assets/dnfast-manifest.json', manifest)
        archive.writestr('assets/dnfast-root-overlay.tar.gz.bin', overlay)

    def fixture(name):
        root = base / name
        root.mkdir(mode=0o700)
        (root / '.tinyagent-root-id').write_text(identity)
        (root / '.tinyagent-root-id').chmod(0o600)
        (root / 'var/lib/dnfast/app-proot' / identity).mkdir(parents=True, mode=0o700)
        for path, data in old.items():
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        return root

    def reject(root):
        before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}
        try: module.upgrade(root, apk)
        except (ValueError, BlockingIOError, OSError): pass
        else: raise AssertionError('Unsafe upgrade accepted')
        assert before == {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}

    root = fixture('busy')
    (root / 'var/lib/dnfast/app-proot' / identity / 'transactions').mkdir()
    reject(root)
    root = fixture('locked')
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    try: reject(root)
    finally: os.close(fd)
    root = fixture('unknown')
    (root / 'usr/bin/dnfast').write_bytes(b'unknown')
    reject(root)
    root = fixture('symlink')
    (root / 'usr/bin/dnfast').unlink()
    (root / 'usr/bin/dnfast').symlink_to(apk)
    reject(root)
    root = fixture('interrupted')
    replace = module.os.replace
    def interrupt(source, target, **kwargs):
        if target == 'dnfast-executor': raise OSError('injected publication interruption')
        return replace(source, target, **kwargs)
    module.os.replace = interrupt
    try:
        try: module.upgrade(root, apk)
        except OSError as error: assert 'injected' in str(error)
        else: raise AssertionError('Interruption not injected')
    finally: module.os.replace = replace
    module.upgrade(root, apk)
    module.upgrade(root, apk)
    assert all((root / name).read_bytes() == data for name, data in new.items())
    assert (root / '.tinyagent-root-id').read_text() == identity
    for name, data in old.items():
        assert (root / 'var/lib/dnfast-upgrades' / module.BACKUP / identity / name.replace('/', '_')).read_bytes() == data

    root = fixture('checked-history')
    partial = root / 'usr/bin/dnfast.tinyagent-new'
    partial.write_bytes(new['usr/bin/dnfast'][:3])
    state = root / 'var/lib/dnfast/app-proot' / identity
    history = state / 'transactions' / 'historical' / 'record.json'
    history.parent.mkdir(parents=True, mode=0o700)
    history.write_bytes(b'preserved historical journal bytes')
    original = history.read_bytes()
    capture = io.StringIO()
    with redirect_stdout(capture): module.upgrade(root, apk, 'snapshot')
    checked = capture.getvalue().strip()
    assert len(checked) == 64
    history.write_bytes(original + b'changed after native validation')
    try: module.upgrade(root, apk, checked)
    except ValueError as error: assert 'changed since' in str(error)
    else: raise AssertionError('Changed state was published')
    assert all((root / name).read_bytes() == data for name, data in old.items())
    history.write_bytes(original)
    module.os.replace = interrupt
    try:
        try: module.upgrade(root, apk, checked)
        except OSError as error: assert 'injected' in str(error)
        else: raise AssertionError('Checked interruption not injected')
    finally: module.os.replace = replace
    module.upgrade(root, apk, checked)
    assert history.read_bytes() == original
    assert (root / '.tinyagent-root-id').read_text() == identity
    assert all((root / name).read_bytes() == data for name, data in new.items())
    (state / 'unexpected-link').symlink_to(history)
    try: module.upgrade(root, apk, checked)
    except ValueError as error: assert 'metadata' in str(error)
    else: raise AssertionError('Symlink state was accepted')
print('PASS: empty/checked upgrades, journal bytes, changed state rejection, lock, unknown ELF, symlink, interruption/retry, backups')

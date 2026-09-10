"""Patched APK input must not overwrite the upstream collector's verified cache."""
import hashlib
import importlib.util
from pathlib import Path
import sys
import tempfile
import zipfile
from unittest.mock import patch

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('runtime_staging', root / 'scripts/stage-runtime-assets.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
with tempfile.TemporaryDirectory() as directory:
    fixture = Path(directory)
    artifacts = fixture / 'artifacts'
    artifacts.mkdir()
    original = artifacts / 'opencode-linux-arm64.tar.gz'
    original.write_bytes(b'verified upstream cache')
    patched = artifacts / 'opencode-patched.tar.gz'
    patched.write_bytes(b'patched local runtime')
    fedora = artifacts / 'fedora-44-arm64-rootfs.tar.gz'
    fedora.write_bytes(b'verified Fedora input')
    module.__file__ = str(fixture / 'scripts/stage-runtime-assets.py')
    module.PINS = {fedora.name: hashlib.sha256(fedora.read_bytes()).hexdigest(),
                   original.name: hashlib.sha256(patched.read_bytes()).hexdigest()}
    argv = ['stage-runtime-assets.py', str(artifacts), '--opencode-archive', str(patched)]
    with patch.object(sys, 'argv', argv):
        module.main()
    assert original.read_bytes() == b'verified upstream cache'
    assert (fixture / 'app/src/main/assets' / (original.name + '.bin')).read_bytes() == patched.read_bytes()
    apk = fixture / 'installed.apk'
    with zipfile.ZipFile(apk, 'w') as archive:
        archive.writestr('assets/' + fedora.name + '.bin', fedora.read_bytes())
        archive.writestr('assets/' + original.name + '.bin', patched.read_bytes())
    with patch.object(sys, 'argv', ['stage-runtime-assets.py', str(artifacts), '--installed-apk', str(apk)]):
        module.main()
    assert original.read_bytes() == b'verified upstream cache'
    assert (fixture / 'app/src/main/assets' / (original.name + '.bin')).read_bytes() == patched.read_bytes()
    with zipfile.ZipFile(apk, 'w') as archive:
        archive.writestr('assets/' + fedora.name + '.bin', fedora.read_bytes())
        archive.writestr('assets/' + original.name + '.bin', b'wrong runtime')
    with patch.object(sys, 'argv', ['stage-runtime-assets.py', str(artifacts), '--installed-apk', str(apk)]):
        try:
            module.main()
        except ValueError as error:
            assert 'digest mismatch' in str(error)
        else:
            raise AssertionError('Wrong installed runtime accepted')
    # Old/default callers must still reject an upstream archive at the patched runtime slot.
    with patch.object(sys, 'argv', ['stage-runtime-assets.py', str(artifacts)]):
        try:
            module.main()
        except ValueError as error:
            assert 'digest mismatch' in str(error)
        else:
            raise AssertionError('Wrong runtime accepted')
print('PASS: original cache retained, patched asset staged, wrong runtime still rejected')

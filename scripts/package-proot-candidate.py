"""Package the source-built PRoot with deterministic metadata; no APK mutation."""
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile

root = Path(__file__).resolve().parents[1]
build = root / '.checks/proot-fchmodat2-build'
report = json.loads((build / 'build.json').read_text())
assert report['build_script_sha256'] == hashlib.sha256((root / 'scripts/build-proot-fchmodat2.py').read_bytes()).hexdigest()
assert report['patch_sha256'] == hashlib.sha256((root / 'patches/proot-exitkill.patch').read_bytes()).hexdigest()
assert report['fchmodat2_patch_sha256'] == hashlib.sha256((root / 'patches/proot-fchmodat2.patch').read_bytes()).hexdigest()
output = root / 'runtime/proot-fchmodat2-2.tar.gz'
with output.open('wb') as raw:
    with gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode='w') as archive:
            for name, digest in sorted(report['outputs'].items()):
                data = (build / name).read_bytes()
                assert hashlib.sha256(data).hexdigest() == digest
                entry = tarfile.TarInfo(name)
                entry.size, entry.mode = len(data), 0o755
                archive.addfile(entry, io.BytesIO(data))
report.update(archive=output.name, archive_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
              status='App UID 10154: exact Cargo tar baseline exit2/candidate exit0; full APK integration pending')
(root / 'runtime/proot-fchmodat2-2.json').write_text(json.dumps(report, indent=2) + '\n')
print(report['archive_sha256'])

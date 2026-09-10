"""Refresh the existing private release checkout with an explicit source allowlist."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import argparse

source = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--apk', type=Path, required=True, help='Exact verified APK associated with this source snapshot')
args = parser.parse_args()
assert args.apk.is_file() and args.apk.suffix == '.apk'
destination = source.parent/'github-private/TinyAgent'
assert subprocess.check_output(['git', '-C', str(destination), 'remote', 'get-url', 'origin'], text=True).strip() == 'https://github.com/GPLaider/TinyAgent.git'
snapshot = json.loads((destination/'SOURCE-SNAPSHOT.json').read_text())
names = set(snapshot['files_sha256'])
names.update(str(p.relative_to(source)).replace('\\', '/') for p in (source/'benchmarks/package-manager').glob('*') if p.suffix in {'.py', '.sh', '.md', '.json'})
names.update([
    'native/fd-gate/probe.c', 'native/fd-gate/executor_fd.c',
    'native/fd-gate/dnfast_native.h', 'native/fd-gate/LICENSE', 'native/fd-gate/PROVENANCE.json',
    'app/src/main/java/io/github/gplaider/tinyagent/DnfastResult.java',
    'app/src/debug/java/io/github/gplaider/tinyagent/DnfastResultCheck.java',
    'scripts/collect-pacman-build.py', 'scripts/export-private-source.py',
    'scripts/verify-source-snapshot.py',
    'scripts/check-luna-development-evidence.py',
    'benchmarks/package-manager/luna-development-acceptance.txt',
    'docs/PREVIEW4.md', 'docs/PRERELEASE-4-VALIDATION.md',
])
hashes = {}
raw_normalized = {}
changed = []
for name in sorted(names):
    relative = Path(name)
    assert not relative.is_absolute() and '..' not in relative.parts
    assert relative.suffix not in {'.keystore', '.jks', '.apk', '.bin'}
    original, target = source/relative, destination/relative
    assert original.is_file(), name
    data = original.read_bytes()
    if not target.exists() or target.read_bytes() != data:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, target)
        changed.append(name)
    oid = subprocess.check_output(['git', '-C', str(destination), 'hash-object', '-w', '--path='+name, '--stdin'], input=data).decode().strip()
    canonical = subprocess.check_output(['git', '-C', str(destination), 'cat-file', '--filters', '--path='+name, oid])
    hashes[name] = hashlib.sha256(canonical).hexdigest()
    if canonical != data:
        raw_normalized[name] = hashlib.sha256(data).hexdigest()
snapshot.update(base_commit=subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip(),
                includes_working_tree_changes=True, files_sha256=hashes,
                original_files_sha256_before_git_normalization=raw_normalized,
                file_hash_scope='Git archive bytes after repository checkout filters and EOL attributes; original hashes retained for normalized working files',
                apk_sha256=hashlib.sha256(args.apk.read_bytes()).hexdigest())
(destination/'SOURCE-SNAPSHOT.json').write_text(json.dumps(snapshot, indent=2)+'\n')
print(json.dumps(dict(files=len(hashes), changed=changed), indent=2))

"""Refresh the existing private release checkout with an explicit source allowlist."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

source = Path(__file__).resolve().parents[1]
destination = source.parent/'github-private/TinyAgent'
assert subprocess.check_output(['git', '-C', str(destination), 'remote', 'get-url', 'origin'], text=True).strip() == 'https://github.com/GPLaider/TinyAgent.git'
snapshot = json.loads((destination/'SOURCE-SNAPSHOT.json').read_text())
names = set(snapshot['files_sha256'])
names.update(str(p.relative_to(source)).replace('\\', '/') for p in (source/'benchmarks/package-manager').glob('*') if p.suffix in {'.py', '.sh', '.md', '.json'})
names.update([
    'app/src/main/java/io/github/gplaider/tinyagent/DnfastResult.java',
    'app/src/debug/java/io/github/gplaider/tinyagent/DnfastResultCheck.java',
    'scripts/collect-pacman-build.py', 'scripts/export-private-source.py',
    'docs/PREVIEW4.md', 'docs/PRERELEASE-4-VALIDATION.md',
])
hashes = {}
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
    hashes[name] = hashlib.sha256(data).hexdigest()
snapshot.update(base_commit=subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip(),
                includes_working_tree_changes=True, files_sha256=hashes,
                apk_sha256=hashlib.sha256((source.parent/'artifacts/TinyAgent-0.1.0-preview.4-arm64.apk').read_bytes()).hexdigest())
(destination/'SOURCE-SNAPSHOT.json').write_text(json.dumps(snapshot, indent=2)+'\n')
print(json.dumps(dict(files=len(hashes), changed=changed), indent=2))

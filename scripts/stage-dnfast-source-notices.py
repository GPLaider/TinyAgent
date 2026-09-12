"""Read notices from hash-pinned source RPMs without extracting their paths."""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

root = Path(__file__).resolve().parents[1]
records = json.loads((root / 'runtime/dnfast-additional-source-rpms.json').read_bytes())
targets = {
    'acl-2.4.0-1.fc44.src.rpm': ('acl-2.4.0.tar.gz', ['acl-2.4.0/doc/COPYING', 'acl-2.4.0/doc/COPYING.LGPL']),
    'zlib-ng-2.3.3-3.fc44.src.rpm': ('zlib-ng-2.3.3.tar.gz', ['zlib-ng-2.3.3/LICENSE.md']),
}
notices = []
for record in records:
    name = record['source_rpm']
    source, members = targets[name]
    rpm = root / 'artifacts/native-sources/rpms' / name
    if hashlib.sha256(rpm.read_bytes()).hexdigest() != record['sha256']:
        raise ValueError('Source RPM digest mismatch: ' + name)
    data = subprocess.check_output(['tar', '-xOf', str(rpm), source])
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        for name_in_archive in members:
            member = archive.getmember(name_in_archive)
            if not member.isfile() or member.size > 1024 * 1024:
                raise ValueError('Invalid notice member')
            content = archive.extractfile(member).read()
            relative = 'dnfast-source/' + name + '/' + Path(name_in_archive).name
            target = root / 'app/src/main/assets/licenses' / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            notices.append({'file': relative, 'sha256': hashlib.sha256(content).hexdigest(),
                            'source_rpm': name, 'source_archive': source, 'member': name_in_archive})
(root / 'runtime/dnfast-source-notices.json').write_text(json.dumps(notices, indent=2) + '\n', encoding='utf-8')
print(f'PASS: {len(notices)} notices staged from pinned source RPMs')

"""Stage only notices enumerated and hashed by the original build-image collector."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile

root = Path(__file__).resolve().parents[1]
report = json.loads((root / 'runtime/dnfast-rpm-notices.json').read_bytes())
archive = root / 'artifacts/native-sources/dnfast-rpm-notices.tar'
if hashlib.sha256(archive.read_bytes()).hexdigest() != report['notice_archive_sha256']:
    raise ValueError('Notice archive hash mismatch')
expected = {notice['member']: notice['sha256'] for row in report['packages'] for notice in row['notices']}
payloads = {}
with tarfile.open(archive) as source:
    for member in source:
        path = PurePosixPath(member.name)
        if not member.isfile() or path.is_absolute() or '..' in path.parts or member.name in payloads or member.name not in expected:
            raise ValueError('Invalid notice member: ' + member.name)
        data = source.extractfile(member).read()
        if hashlib.sha256(data).hexdigest() != expected[member.name]:
            raise ValueError('Notice digest mismatch: ' + member.name)
        payloads[member.name] = data
if set(payloads) != set(expected):
    raise ValueError('Missing notices')
for name, data in payloads.items():
    target = root / 'app/src/main/assets/licenses/dnfast-rpm' / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
print(f'PASS: {len(payloads)} notices staged; dependency notice completeness={report["complete_notices"]}')

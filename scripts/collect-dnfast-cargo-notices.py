"""Collect notices from every locked crate source, a superset of linked crates."""
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tarfile
import tomllib

root = Path(__file__).resolve().parents[1]
source = root / 'artifacts/native-sources/dnfast-cargo-sources.tar'
manifest = json.loads((root / 'runtime/dnfast-cargo-sources.json').read_bytes())
with source.open('rb') as stream:
    assert hashlib.file_digest(stream, 'sha256').hexdigest() == manifest['archive_sha256']
target = root / 'artifacts/native-sources/dnfast-cargo-notices.tar'
temporary = target.with_suffix('.part')
records = []
with tarfile.open(source) as sources, tarfile.open(temporary, 'w') as notices:
    for package in manifest['packages']:
        name = package['name'] + '-' + package['version']
        data = sources.extractfile('registry/' + name + '.crate').read()
        assert hashlib.sha256(data).hexdigest() == package['sha256'], name
        with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as crate:
            metadata = tomllib.loads(crate.extractfile(name + '/Cargo.toml').read().decode())['package']
            declared = metadata.get('license-file', '')
            row = {'crate': name, 'license_expression': metadata.get('license'),
                   'declared_license_file': declared, 'notices': []}
            for member in crate.getmembers():
                path = PurePosixPath(member.name)
                assert not path.is_absolute() and '..' not in path.parts, name + ': invalid archive path'
                if not member.isfile():
                    continue
                if not (path.name.lower().startswith(('license', 'copying', 'copyright', 'notice'))
                        or (declared and member.name == name + '/' + declared)):
                    continue
                assert member.size <= 2 * 1024 * 1024, name + ': oversized notice'
                content = crate.extractfile(member).read()
                entry = tarfile.TarInfo(member.name)
                entry.size, entry.mode = len(content), 0o644
                notices.addfile(entry, io.BytesIO(content))
                row['notices'].append({'member': member.name, 'sha256': hashlib.sha256(content).hexdigest()})
            records.append(row)
temporary.replace(target)
with target.open('rb') as stream:
    digest = hashlib.file_digest(stream, 'sha256').hexdigest()
missing = [row['crate'] for row in records if not row['notices']]
report = {'scope': 'Notices from all locked registry crate archives, including dev and other-target dependencies; not a compiled dependency attribution',
          'source_archive_sha256': manifest['archive_sha256'], 'archive_sha256': digest,
          'packages': records, 'without_notice_files': missing}
(root / 'runtime/dnfast-cargo-notices.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'packages': len(records), 'notice_files': sum(len(row['notices']) for row in records),
                  'without_notice_files': missing, 'archive_sha256': digest}))

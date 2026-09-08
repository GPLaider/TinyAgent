"""Collect pinned native sources/notices; this does not claim binary reproducibility."""
import hashlib
import io
import json
from pathlib import Path
import tarfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/native-sources'
PINS = [
    ('proot-5.1.107.92.zip', 'https://github.com/termux/proot/archive/v5.1.107.92.zip', '29385d1ddb619a9c4449ab512bfd55032034b22f724ddf98fc95ff300ea32135'),
    ('talloc-2.4.3.tar.gz', 'https://www.samba.org/ftp/talloc/talloc-2.4.3.tar.gz', 'dc46c40b9f46bb34dd97fe41f548b0e8b247b77a918576733c528e83abd854dd'),
    ('libandroid-shmem-0.7.tar.gz', 'https://github.com/termux/libandroid-shmem/archive/refs/tags/v0.7.tar.gz', '1e5ff8459bc0a8c229dd8a94b27d119987e09ef3414331c2b5ebfff20b98e867'),
]
TERMUX_REVISION = 'ff422d48d23ad12e8ffba021c2fa3a5c6b4f138e'

def fetch(url, target, expected=None):
    if not target.exists():
        with urllib.request.urlopen(url, timeout=60) as response:
            assert response.url.startswith('https://')
            data = response.read(128 * 1024 * 1024 + 1)
        assert len(data) <= 128 * 1024 * 1024
        if expected: assert hashlib.sha256(data).hexdigest() == expected, target.name
        target.write_bytes(data)
    data = target.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if expected: assert digest == expected, target.name
    return data, dict(file=target.name, url=url, sha256=digest, bytes=len(data))

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    records = []
    for name, url, expected in PINS:
        data, record = fetch(url, OUT / name, expected)
        notices = []
        if name.endswith('.zip'):
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                for member in archive.infolist():
                    if not member.is_dir() and Path(member.filename).name.upper().startswith(('COPYING', 'LICENSE')):
                        assert member.file_size < 1024 * 1024
                        notices.append((member.filename, archive.read(member)))
        else:
            with tarfile.open(fileobj=io.BytesIO(data)) as archive:
                for member in archive:
                    if member.isfile() and Path(member.name).name.upper().startswith(('COPYING', 'LICENSE')):
                        assert member.size < 1024 * 1024
                        notices.append((member.name, archive.extractfile(member).read()))
        assert notices, 'No notices found in ' + name
        record['notices'] = []
        for index, (member, content) in enumerate(notices):
            target = OUT / (name + '.' + str(index) + '.license.txt')
            target.write_bytes(content)
            record['notices'].append(dict(source_member=member, file=target.name, sha256=hashlib.sha256(content).hexdigest()))
        records.append(record)
        print(name, 'verified;', len(notices), 'license files', flush=True)
    license_dir = ROOT / 'app/src/main/assets/licenses'
    license_dir.mkdir(parents=True, exist_ok=True)
    for record in records:
        for notice in record['notices']:
            (license_dir / notice['file']).write_bytes((OUT / notice['file']).read_bytes())
    # The complete pinned license is versioned with the source; rebuilding must
    # not depend on reaching GNU again for these identical bytes.
    cached_license = OUT / 'GPL-3.0.txt'
    bundled_license = license_dir / 'GPL-3.0.txt'
    if not cached_license.exists() and bundled_license.is_file():
        cached_license.write_bytes(bundled_license.read_bytes())
    gpl, gpl_record = fetch('https://www.gnu.org/licenses/gpl-3.0.txt', cached_license,
                            '3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986')
    assert b'GNU GENERAL PUBLIC LICENSE' in gpl and b'Version 3' in gpl
    (license_dir / 'GPL-3.0.txt').write_bytes(gpl)
    url = 'https://github.com/termux/termux-packages/archive/' + TERMUX_REVISION + '.tar.gz'
    _, recipe = fetch(url, OUT / ('termux-packages-' + TERMUX_REVISION + '.tar.gz'),
                      '10f95083c4f8444d412adfbe36d6cd2439e6a771fa72ebaa0873f92488489741')
    report = dict(sources=records, additional_license=gpl_record, build_recipes=recipe, recipe_revision=TERMUX_REVISION,
                  scope='Sources and complete notice files collected. Rebuilt binary equivalence, repository signatures, dependency closure and distribution compliance remain unverified.')
    (ROOT / 'evidence/native-source-collection.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')

if __name__ == '__main__': main()

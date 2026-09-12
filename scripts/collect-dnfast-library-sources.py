"""Fetch exact source RPMs for bundled libraries; hashes are not signature proof."""
import hashlib
import json
from pathlib import Path
import re
import urllib.request

root = Path(__file__).resolve().parents[1]
packages = json.loads((root / 'runtime/dnfast-rpm-notices.json').read_bytes())['packages']
destination = root / 'artifacts/native-sources/rpms'
destination.mkdir(parents=True, exist_ok=True)
receipt = root / 'runtime/dnfast-library-sources.json'
known = json.loads(receipt.read_bytes())['sources'] if receipt.exists() else []
known += json.loads((root / 'runtime/dnfast-additional-source-rpms.json').read_bytes())
known = {row['source_rpm']: row for row in known if 'sha256' in row}
records = []

for filename in sorted({package['source_rpm'] for package in packages}):
    assert re.fullmatch(r'[A-Za-z0-9_.+~-]+\.src\.rpm', filename), 'Invalid source RPM name'
    name, version, release = filename[:-8].rsplit('-', 2)
    url = f'https://kojipkgs.fedoraproject.org/packages/{name}/{version}/{release}/src/{filename}'
    target = destination / filename
    temporary = target.with_suffix('.part')
    previous = known.get(filename)
    try:
        if previous and target.is_file():
            with target.open('rb') as cached:
                digest = hashlib.file_digest(cached, 'sha256').hexdigest()
            assert previous['url'] == url and previous['sha256'] == digest, 'Cached source mismatch'
        else:
            with urllib.request.urlopen(url, timeout=45) as response, temporary.open('wb') as output:
                size = 0
                while block := response.read(1024 * 1024):
                    size += len(block)
                    if size > 512 * 1024 * 1024:
                        raise ValueError('Source RPM exceeds 512 MiB limit')
                    output.write(block)
            with temporary.open('rb') as downloaded:
                assert downloaded.read(4) == bytes.fromhex('edabeedb'), 'Response is not an RPM'
                downloaded.seek(0)
                digest = hashlib.file_digest(downloaded, 'sha256').hexdigest()
            if previous:
                assert previous['url'] == url and previous['sha256'] == digest, 'Downloaded source changed'
            temporary.replace(target)
        records.append({'source_rpm': filename, 'url': url, 'bytes': target.stat().st_size,
                        'sha256': digest, 'signature_verified': False})
        print(filename + ' collected', flush=True)
    except Exception as error:
        records.append({'source_rpm': filename, 'url': url, 'error': str(error)})
        print(filename + ' failed: ' + str(error), flush=True)
    report = {'scope': 'Exact source RPM filenames from the original build image; HTTPS downloads, no RPM signature verification',
              'expected': len({package['source_rpm'] for package in packages}), 'sources': records,
              'complete': len(records) == len({package['source_rpm'] for package in packages}) and all('sha256' in row for row in records)}
    pending = receipt.with_suffix('.part')
    pending.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    pending.replace(receipt)

if not report['complete']:
    raise SystemExit('Source RPM collection incomplete; see receipt')

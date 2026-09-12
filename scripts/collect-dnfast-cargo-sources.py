"""Export Cargo.lock registry source archives from the existing build cache."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile
import tomllib
import urllib.request

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('lock', type=Path)
parser.add_argument('cargo_home', type=Path)
parser.add_argument('output', type=Path)
parser.add_argument('--fetch-missing', action='store_true')
args = parser.parse_args()
lock = args.lock.read_bytes()
packages = tomllib.loads(lock.decode())['package']
args.output.mkdir(parents=True, exist_ok=True)
target = args.output / 'dnfast-cargo-sources.tar'
records, missing = [], []
with tarfile.open(target.with_suffix('.part'), 'w') as output:
    for package in packages:
        source = package.get('source')
        if source is None: continue  # Workspace sources are in the pinned source export.
        name = package['name'] + '-' + package['version'] + '.crate'
        if not re.fullmatch(r'[A-Za-z0-9_.+-]+\.crate', name):
            raise ValueError('Unexpected crate filename')
        candidates = list((args.cargo_home / 'registry/cache').glob('*/' + name))
        candidates = [p for p in candidates if p.is_file() and not p.is_symlink()]
        if not candidates and args.fetch_missing and source == 'registry+https://github.com/rust-lang/crates.io-index':
            downloaded = args.output / name
            if downloaded.exists():
                data = downloaded.read_bytes()
            else:
                url = 'https://static.crates.io/crates/' + package['name'] + '/' + name
                with urllib.request.urlopen(url, timeout=60) as response:
                    data = response.read(32 * 1024 * 1024 + 1)
            if len(data) > 32 * 1024 * 1024 or hashlib.sha256(data).hexdigest() != package['checksum']:
                raise ValueError('Downloaded source checksum mismatch: ' + name)
            downloaded.write_bytes(data)
            candidates = [downloaded]
        if not source.startswith('registry+') or not candidates:
            missing.append({'name': name, 'source': source})
            continue
        data = candidates[0].read_bytes()
        if hashlib.sha256(data).hexdigest() != package['checksum']:
            raise ValueError('Cached source checksum mismatch: ' + name)
        entry = tarfile.TarInfo('registry/' + name)
        entry.size, entry.mode = len(data), 0o644
        output.addfile(entry, io.BytesIO(data))
        records.append({'name': package['name'], 'version': package['version'],
                        'source': source, 'sha256': package['checksum'], 'bytes': len(data)})
    entry = tarfile.TarInfo('Cargo.lock')
    entry.size, entry.mode = len(lock), 0o644
    output.addfile(entry, io.BytesIO(lock))
target.with_suffix('.part').replace(target)
report = {'lock_sha256': hashlib.sha256(lock).hexdigest(), 'packages': records,
          'missing': missing, 'complete_locked_registry_sources': not missing,
          'archive_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
          'scope': 'Exact locked crate sources, including dev and target-specific dependencies; not a compiled dependency or notice inventory'}
(args.output / 'dnfast-cargo-sources.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({key: value for key, value in report.items() if key not in ('packages', 'missing')}))
print('missing_packages=' + str(len(missing)))
print('exported_packages=' + str(len(records)))

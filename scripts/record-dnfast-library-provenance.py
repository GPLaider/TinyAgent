"""Match original ARM build attribution against every pinned overlay library."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('build_manifest', type=Path)
args = parser.parse_args()
raw = args.build_manifest.read_bytes()
original = json.loads(raw)
overlay = json.loads((ROOT / 'runtime/dnfast-16c6887-manifest.json').read_bytes())
if original['candidate_commit'] != overlay['source_commit']:
    raise ValueError('Source revisions differ')
libraries = []
for path, digest in sorted(overlay['files'].items()):
    if not path.startswith(overlay['library_prefix'].lstrip('/') + '/'):
        continue
    name = Path(path).name
    if original['files'].get('lib/' + name) != digest:
        raise ValueError('Original library hash differs: ' + name)
    libraries.append(dict(file=path, sha256=digest, package=original['library_packages'][name]))
if len(libraries) != len(original['library_packages']):
    raise ValueError('Incomplete library mapping')
for original_path, overlay_path in [('bin/dnfast', '/usr/bin/dnfast'), ('bin/dnfast-executor', '/usr/libexec/dnfast-executor')]:
    if original['files'][original_path] != overlay['binaries'][overlay_path]['source_sha256']:
        raise ValueError('Original executable hash differs: ' + original_path)
record = dict(source_commit=overlay['source_commit'],
              original_build_manifest_sha256=hashlib.sha256(raw).hexdigest(),
              original_source_archive_sha256=original['source_archive_sha256'],
              attribution='Original ARM build rpm -qf records, matched by file hash; not a fresh RPM signature verification',
              libraries=libraries, tool_packages=original['tool_packages'],
              remaining=['Collect matching dependency source RPMs and license notices', 'Collect pinned Rust dependency sources and notices'])
(ROOT / 'runtime/dnfast-library-provenance.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
print(f'PASS: {len(libraries)} libraries matched, {len(set(row["package"] for row in libraries))} exact package versions; both original executable hashes matched')

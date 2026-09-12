"""Package the pinned patched ARM backend without replacing upstream downloads."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import tarfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('binary', type=Path)
parser.add_argument('output', type=Path)
parser.add_argument('--manifest', type=Path, help='Explicit candidate manifest; default remains the shipped runtime')
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
manifest_path = args.manifest or root / 'runtime/opencode-snapshot-12.json'
manifest = json.loads(manifest_path.read_text())
with args.binary.open('rb') as stream:
    assert hashlib.file_digest(stream, 'sha256').hexdigest() == manifest['binary_sha256']
assert args.binary.stat().st_size == manifest['binary_bytes']
assert args.output.resolve() != args.binary.resolve()
args.output.parent.mkdir(parents=True, exist_ok=True)
partial = args.output.with_suffix(args.output.suffix + '.part')
with partial.open('wb') as raw:
    with gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as zipped:
        with tarfile.open(fileobj=zipped, mode='w') as archive:
            item = tarfile.TarInfo('opencode')
            item.size = manifest['binary_bytes']
            item.mode = 0o755
            with args.binary.open('rb') as binary:
                archive.addfile(item, binary)
with tarfile.open(partial, 'r:gz') as archive:
    assert archive.getnames() == ['opencode']
    with archive.extractfile('opencode') as binary:
        assert hashlib.file_digest(binary, 'sha256').hexdigest() == manifest['binary_sha256']
with partial.open('rb') as stream:
    manifest['archive_sha256'] = hashlib.file_digest(stream, 'sha256').hexdigest()
manifest['archive_bytes'] = partial.stat().st_size
partial.replace(args.output)
manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps({'archive': str(args.output), 'sha256': manifest['archive_sha256'],
    'bytes': manifest['archive_bytes'], 'packaged_binary_verified': True}))

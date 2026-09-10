import hashlib
import json
import os
import sys
from pathlib import Path

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/work/direct/dnfast')
path = root / 'manifest.json'
data = json.loads(path.read_text())
data['packaging'] = {
    'original_archive_sha256': hashlib.sha256((root.parent.parent / 'original.tar.gz').read_bytes()).hexdigest(),
    'original_binary_hashes': {name: value for name, value in data['files'].items() if name.startswith('bin/')},
    'interpreter': os.environ['DNFAST_GUEST_ROOT'] + '/dnfast/lib/ld-linux-aarch64.so.1',
    'dt_rpath': '$ORIGIN/../lib',
    'scope': 'phone benchmark bundle; source unchanged; direct exec supports /proc/self/exe reexec',
}
for name in data['files']:
    data['files'][name] = hashlib.sha256((root / name).read_bytes()).hexdigest()
path.write_text(json.dumps(data, indent=2))

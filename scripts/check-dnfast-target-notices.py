"""Check captured ARM64 normal/build dependencies against retained crate notices."""
import hashlib
import json
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1] / 'runtime'
tree = (root / 'dnfast-target-tree.txt').read_bytes()
notice_data = (root / 'dnfast-cargo-notices.json').read_bytes()
notices = {row['crate']: row for row in json.loads(notice_data)['packages']}
invocation = json.loads((root / 'dnfast-target-tree-invocation.json').read_bytes())
assert invocation['exit'] == 0
assert '--target=aarch64-unknown-linux-gnu' in invocation['argv']
assert '--edges=normal,build' in invocation['argv']
packages = set()
for line in tree.decode().splitlines():
    if not line.strip():
        continue
    match = re.match(r'^([A-Za-z0-9_-]+) v(\S+)', line)
    assert match, 'Unexpected cargo tree line: ' + line
    if '(/work/source/' in line:
        continue
    package = match[1] + '-' + match[2]
    assert package in notices, 'Dependency missing from source inventory: ' + package
    packages.add(package)
missing = sorted(package for package in packages if not notices[package]['notices'])
report = {'scope': 'Captured default-feature ARM64 normal/build dependency graph, not ELF symbol attribution',
          'tree_sha256': hashlib.sha256(tree).hexdigest(),
          'notices_report_sha256': hashlib.sha256(notice_data).hexdigest(),
          'packages': sorted(packages), 'without_notice_files': missing}
(root / 'dnfast-target-notices.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'target_packages': len(packages), 'without_notice_files': missing}))
assert not missing, 'Target dependency notice files are missing'

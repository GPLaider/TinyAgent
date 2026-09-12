"""Export the exact dnfast commit and its notice, without using checkout changes."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
REVISION = '1449710f35e1079c5999a3d6cc41800d4b432a4d'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('checkout', type=Path)
    args = parser.parse_args()
    checkout = args.checkout.resolve(strict=True)
    commit = subprocess.check_output(['git', '-C', str(checkout), 'rev-parse', REVISION + '^{commit}']).decode().strip()
    if commit != REVISION:
        raise ValueError('dnfast revision mismatch')
    notice = subprocess.check_output(['git', '-C', str(checkout), 'show', REVISION + ':LICENSE'])
    output = ROOT / 'artifacts/native-sources'
    output.mkdir(parents=True, exist_ok=True)
    archive = output / ('dnfast-' + REVISION + '.tar')
    partial = archive.with_suffix('.tar.part')
    subprocess.run(['git', '-c', 'core.autocrlf=false', '-c', 'core.eol=lf', '-C', str(checkout), 'archive', '--format=tar',
                    '--prefix=dnfast-' + REVISION + '/', '--output=' + str(partial), REVISION], check=True)
    with tarfile.open(partial) as source:
        prefix = 'dnfast-' + REVISION + '/'
        if source.extractfile(prefix + 'LICENSE').read() != notice:
            raise ValueError('Archive notice mismatch')
        for name in ('Cargo.lock', 'Cargo.toml', 'crates/dnfast-cli/Cargo.toml'):
            source.getmember(prefix + name)
    partial.replace(archive)
    notices = ROOT / 'app/src/main/assets/licenses'
    notices.mkdir(parents=True, exist_ok=True)
    (notices / 'dnfast-LICENSE.txt').write_bytes(notice)
    record = dict(source_commit=REVISION, archive=archive.name,
                  archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                  notice='dnfast-LICENSE.txt', notice_sha256=hashlib.sha256(notice).hexdigest(),
                  scope='Pinned source export only; not proof of binary reproducibility or dependency-source completeness')
    (ROOT / 'runtime/dnfast-source-export.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()

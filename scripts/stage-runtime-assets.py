"""Stage already verified runtime archives into the APK; no download or extraction."""
import argparse
import hashlib
from pathlib import Path
import shutil
import zipfile

PINS = {
    'fedora-44-arm64-rootfs.tar.gz': '3a3661a77d5fdb1e4bd10be484142683630c1ffb4c371931d46a42459fd4c125',
    'opencode-linux-arm64.tar.gz': '5139469d4fa9b7371129a956765d7ede425232c4d6bdbb07ab86f966c56fe2a2',
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('artifacts', type=Path)
    inputs = parser.add_mutually_exclusive_group()
    inputs.add_argument('--opencode-archive', type=Path, help='Patched runtime input, separate from the upstream download cache')
    inputs.add_argument('--installed-apk', type=Path, help='Reuse exact runtime assets from the installed APK; retain all pinned hashes')
    args = parser.parse_args()
    target = Path(__file__).resolve().parents[1] / 'app/src/main/assets'
    target.mkdir(parents=True, exist_ok=True)
    for name, digest in PINS.items():
        partial = target / (name + '.bin.part')
        if args.installed_apk:
            with zipfile.ZipFile(args.installed_apk) as installed:
                entry = installed.getinfo('assets/' + name + '.bin')
                if entry.file_size > 256 * 1024 * 1024:
                    raise ValueError('Oversized runtime asset: ' + name)
                with installed.open(entry) as source, partial.open('wb') as destination:
                    shutil.copyfileobj(source, destination)
        else:
            source = args.opencode_archive if name == 'opencode-linux-arm64.tar.gz' and args.opencode_archive else args.artifacts / name
            shutil.copyfile(source, partial)
        with partial.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != digest:
                raise ValueError('Runtime archive digest mismatch: ' + name)
        # AGP transparently expands assets ending in .gz. Preserve the signed bytes.
        partial.replace(target / (name + '.bin'))
        (target / name).unlink(missing_ok=True)
        print('Verified and staged:', name)


if __name__ == '__main__':
    main()

"""Stage already verified runtime archives into the APK; no download or extraction."""
import argparse
import hashlib
from pathlib import Path
import shutil

PINS = {
    'fedora-44-arm64-rootfs.tar.gz': '3a3661a77d5fdb1e4bd10be484142683630c1ffb4c371931d46a42459fd4c125',
    'opencode-linux-arm64.tar.gz': '70baf769395ca4e7a68924026530c390eace194f3b7e4919d4efcb2aa2eed3c0',
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('artifacts', type=Path)
    args = parser.parse_args()
    target = Path(__file__).resolve().parents[1] / 'app/src/main/assets'
    target.mkdir(parents=True, exist_ok=True)
    for name, digest in PINS.items():
        partial = target / (name + '.bin.part')
        shutil.copyfile(args.artifacts / name, partial)
        with partial.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != digest:
                raise ValueError('Runtime archive digest mismatch: ' + name)
        # AGP transparently expands assets ending in .gz. Preserve the signed bytes.
        partial.replace(target / (name + '.bin'))
        (target / name).unlink(missing_ok=True)
        print('Verified and staged:', name)


if __name__ == '__main__':
    main()

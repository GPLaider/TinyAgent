"""Verify the pinned single-layer Fedora OCI image and stage its original gzip layer.

No root filesystem is extracted on the Windows host. Multi-layer images require
an OCI implementation; this script deliberately rejects them.
"""
import gzip
import hashlib
import io
import json
import tarfile
import argparse
from pathlib import Path, PurePosixPath

ROOT = Path('D:/TinyAgent-work/artifacts')
IMAGE = ROOT / 'Fedora-Container-Base-Generic-Minimal-44-1.7.aarch64.oci.tar.xz'
PIN = '2c00fc0e7890a5bfecbd243561e5a2d07d2661667e1b897eab549b83f6b1db9a'


def safe_members(members):
    names = {}
    for member in members:
        path = PurePosixPath(member.name)
        if path.is_absolute() or '..' in path.parts or not path.parts:
            raise ValueError('Unsafe archive member path')
        if path in names or any(p.startswith('.wh.') for p in path.parts):
            raise ValueError('Duplicate path or unsupported whiteout')
        if not (member.isfile() or member.isdir() or member.issym() or member.islnk()):
            raise ValueError('Unsupported archive member type')
        names[path] = member
    for path, member in names.items():
        if any(parent in names and not names[parent].isdir() for parent in path.parents):
            raise ValueError('Archive writes through a non-directory ancestor')
        if member.islnk():
            target = names.get(PurePosixPath(member.linkname))
            if target is None or not target.isfile():
                raise ValueError('Hardlink must target an archive regular file')


def main():
    global ROOT, IMAGE
    parser = argparse.ArgumentParser()
    parser.add_argument('artifacts', type=Path, nargs='?', default=ROOT)
    ROOT = parser.parse_args().artifacts
    IMAGE = ROOT / IMAGE.name
    with IMAGE.open('rb') as source:
        assert hashlib.file_digest(source, 'sha256').hexdigest() == PIN, 'Fedora checksum mismatch'
    with tarfile.open(IMAGE) as archive:
        def blob(descriptor):
            algorithm, digest = descriptor['digest'].split(':')
            assert algorithm == 'sha256' and len(digest) == 64
            data = archive.extractfile('blobs/sha256/' + digest).read()
            assert len(data) == descriptor['size']
            assert hashlib.sha256(data).hexdigest() == digest
            return data
        index = json.load(archive.extractfile('index.json'))
        assert len(index['manifests']) == 1
        manifest = json.loads(blob(index['manifests'][0]))
        config = json.loads(blob(manifest['config']))
        assert config['architecture'] == 'arm64' and config['os'] == 'linux'
        assert len(manifest['layers']) == 1 and len(config['rootfs']['diff_ids']) == 1
        descriptor = manifest['layers'][0]
        assert descriptor['mediaType'] == 'application/vnd.oci.image.layer.v1.tar+gzip'
        compressed = blob(descriptor)
        raw = gzip.decompress(compressed)
        assert 'sha256:' + hashlib.sha256(raw).hexdigest() == config['rootfs']['diff_ids'][0]
        with tarfile.open(fileobj=io.BytesIO(raw)) as layer:
            members = layer.getmembers()
            safe_members(members)
        output = ROOT / 'fedora-44-arm64-rootfs.tar.gz'
        output.write_bytes(compressed)
        report = dict(source_sha256=PIN, layer_sha256=descriptor['digest'],
                      diff_id=config['rootfs']['diff_ids'][0], members=len(members),
                      rootfs_bytes=len(raw), file=output.name,
                      scope='Verified staging only; not installed or booted')
        (ROOT / 'fedora-rootfs-staging.json').write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2))


def check():
    file = tarfile.TarInfo('usr/bin/bash')
    safe_members([file])
    for path in ('../outside', '/absolute'):
        try:
            safe_members([tarfile.TarInfo(path)])
        except ValueError:
            pass
        else:
            raise AssertionError(path)
    link = tarfile.TarInfo('usr')
    link.type = tarfile.SYMTYPE
    link.linkname = '/outside'
    try:
        safe_members([link, file])
    except ValueError:
        pass
    else:
        raise AssertionError('symlink ancestor accepted')


if __name__ == '__main__':
    check()
    main()

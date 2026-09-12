"""Upgrade the known pre-memfd runtime only when its original root has no journals.

Run inside app-owned Fedora before the backend starts. The root flock covers
validation, durable backups and publication; interrupted publication is resumable.
Existing transactions require the separate matching-runtime recovery procedure.
"""
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import sys
import tarfile
import zipfile

MANIFEST = 'ec8599eb4b44266abbbcafa0952a67d29d96d4ff5572566ad403c0c425492699'
BACKUP = '16c6887-to-1449710'
OLD = {'usr/bin/dnfast': '91090c65fd5afa01a4a99b54c655fd6474b2ea54973af7ff6458b63c4af99c74',
       'usr/libexec/dnfast-executor': '5e856901078349c54b5fa77a72961b0f6c65d540eb86b535ab98620e2c3e8cec'}

def digest(data):
    return hashlib.sha256(data).hexdigest()

def upgrade(root, apk, checked_state=None):
    with zipfile.ZipFile(apk) as package:
        assert package.getinfo('assets/dnfast-manifest.json').file_size < 1024 * 1024
        raw = package.read('assets/dnfast-manifest.json')
        if digest(raw) != MANIFEST:
            raise ValueError('Upgrade manifest mismatch')
        manifest = json.loads(raw)
        assert package.getinfo('assets/dnfast-root-overlay.tar.gz.bin').file_size < 64 * 1024 * 1024
        overlay = package.read('assets/dnfast-root-overlay.tar.gz.bin')
    if digest(overlay) != manifest['overlay_sha256']:
        raise ValueError('Upgrade overlay mismatch')
    payloads = {}
    with io.BytesIO(overlay) as compressed, tarfile.open(fileobj=compressed) as archive:
        for member in archive:
            if not member.isfile() or member.name not in manifest['files'] or member.name in payloads:
                raise ValueError('Unexpected upgrade member')
            data = archive.extractfile(member).read()
            if digest(data) != manifest['files'][member.name]:
                raise ValueError('Upgrade member mismatch')
            payloads[member.name] = data
    if set(payloads) != set(manifest['files']):
        raise ValueError('Incomplete upgrade')
    # Every member is now held as verified bytes; the compressed input is unused.
    del overlay
    rootfd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        fcntl.flock(rootfd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        owner = os.fstat(rootfd).st_uid
        if stat.S_IMODE(os.fstat(rootfd).st_mode) != 0o700:
            raise ValueError('Root permissions differ')

        def directory(relative, create=False):
            fd = os.dup(rootfd)
            try:
                for part in relative.split('/'):
                    if part in ('', '.', '..'):
                        raise ValueError('Invalid upgrade directory')
                    if create:
                        try:
                            os.mkdir(part, 0o700, dir_fd=fd)
                            os.fsync(fd)
                        except FileExistsError: pass
                    following = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                    os.close(fd)
                    fd = following
                    if os.fstat(fd).st_uid != owner:
                        raise ValueError('Upgrade directory owner differs')
                return fd
            except BaseException:
                os.close(fd)
                raise

        def read(relative):
            parent, name = relative.rsplit('/', 1) if '/' in relative else ('', relative)
            fd = directory(parent) if parent else os.dup(rootfd)
            try:
                item = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
                with os.fdopen(item, 'rb') as stream:
                    info = os.fstat(stream.fileno())
                    if not stat.S_ISREG(info.st_mode) or info.st_uid != owner or info.st_nlink != 1:
                        raise ValueError('Upgrade file metadata differs: ' + relative)
                    return stream.read(), info
            finally: os.close(fd)

        identity, info = read('.tinyagent-root-id')
        if not re.fullmatch(b'[0-9a-f]{64}', identity) or stat.S_IMODE(info.st_mode) != 0o600:
            raise ValueError('Invalid existing root ID')
        state = directory('var/lib/dnfast/app-proot/' + identity.decode())
        try:
            if stat.S_IMODE(os.fstat(state).st_mode) != 0o700:
                raise ValueError('Package state permissions differ')
            # Reject every entry, including symlinks, rather than bounded traversal.
            # A fresh failed launcher has created the state directory but no entries.
            if checked_state is None and os.listdir(state):
                raise ValueError('Existing package state requires matching-runtime recovery; preserved')
            if checked_state is not None:
                records = []
                def walk(fd, prefix=''):
                    for name in sorted(os.listdir(fd)):
                        info = os.stat(name, dir_fd=fd, follow_symlinks=False)
                        if info.st_uid != owner or not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
                            raise ValueError('Invalid package state metadata')
                        child = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | (os.O_DIRECTORY if stat.S_ISDIR(info.st_mode) else 0), dir_fd=fd)
                        try:
                            opened = os.fstat(child)
                            if (opened.st_ino, opened.st_dev, opened.st_mode) != (info.st_ino, info.st_dev, info.st_mode):
                                raise ValueError('Package state changed during inspection')
                            entry = [prefix + name, info.st_mode, info.st_uid, info.st_gid]
                            if stat.S_ISDIR(info.st_mode):
                                records.append(entry)
                                walk(child, prefix + name + '/')
                            else:
                                if info.st_nlink != 1: raise ValueError('Linked package state file')
                                with os.fdopen(os.dup(child), 'rb') as stream:
                                    entry.append(hashlib.file_digest(stream, 'sha256').hexdigest())
                                records.append(entry)
                        finally: os.close(child)
                walk(state)
                state_digest = digest(identity + json.dumps(records, separators=(',', ':')).encode())
                if checked_state == 'snapshot':
                    print(state_digest)
                    return
                if not re.fullmatch('[0-9a-f]{64}', checked_state) or checked_state != state_digest:
                    raise ValueError('Package state changed since authenticated validation; preserved')
        finally: os.close(state)
        previous = {}
        for name, expected in OLD.items():
            data, _ = read(name)
            if digest(data) not in (expected, manifest['files'][name]):
                raise ValueError('Unknown installed executable: ' + name)
            previous[name] = data
        backup = 'var/lib/dnfast-upgrades/' + BACKUP + '/' + identity.decode()

        def publish(relative, data, mode):
            parent, name = relative.rsplit('/', 1)
            fd = directory(parent, create=True)
            temp = name + '.tinyagent-new'
            try:
                try:
                    out = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode, dir_fd=fd)
                except FileExistsError:
                    saved, _ = read(parent + '/' + temp)
                    if not data.startswith(saved):
                        raise ValueError('Interrupted staging differs; preserved')
                    out = os.open(temp, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW, dir_fd=fd)
                    with os.fdopen(out, 'wb') as stream:
                        info = os.fstat(stream.fileno())
                        if info.st_size != len(saved) or info.st_uid != owner or info.st_nlink != 1:
                            raise ValueError('Interrupted staging changed; preserved')
                        if saved != data:
                            stream.write(data[len(saved):])
                            stream.flush()
                        os.fsync(stream.fileno())
                else:
                    with os.fdopen(out, 'wb') as stream:
                        stream.write(data)
                        stream.flush()
                        os.fsync(stream.fileno())
                os.replace(temp, name, src_dir_fd=fd, dst_dir_fd=fd)
                os.fsync(fd)
            finally: os.close(fd)

        for name, expected in OLD.items():
            saved = backup + '/' + name.replace('/', '_')
            try: data, _ = read(saved)
            except FileNotFoundError:
                data = previous[name]
                if digest(data) != expected:
                    raise ValueError('Missing original executable backup')
                publish(saved, data, 0o600)
            if digest(data) != expected:
                raise ValueError('Original executable backup differs')
        # New private libraries first. Each executable is then atomically replaced.
        for name in sorted(payloads, key=lambda name: name in OLD):
            payload = payloads.pop(name)
            try: current, _ = read(name)
            except FileNotFoundError: current = None
            if current == payload: continue
            if current is not None and name not in OLD:
                raise ValueError('Existing private library differs; preserved')
            publish(name, payload, 0o755)
        if read('.tinyagent-root-id')[0] != identity:
            raise ValueError('Root ID changed during upgrade')
        for name, expected in manifest['files'].items():
            if digest(read(name)[0]) != expected:
                raise ValueError('Published upgrade differs')
        print(json.dumps({'upgrade': BACKUP, 'original_root_updated': True,
                          'original_binaries_preserved': True, 'package_state_was_empty': checked_state is None,
                          'checked_state': checked_state}))
    finally:
        os.close(rootfd)

if __name__ == '__main__':
    upgrade(Path('/'), Path(sys.argv[1]))

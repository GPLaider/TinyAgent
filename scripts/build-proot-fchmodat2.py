"""Build the pinned Android ARM64 PRoot candidate; never replace APK inputs.

Uses the upstream object list and installed NDK, linking the separately pinned
Termux dependencies. This is not a from-source rebuild of those dependencies.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / '.checks/proot-fchmodat2-build'
NDK = Path.home() / 'AppData/Local/Android/Sdk/ndk/28.0.13004108'
BIN = NDK / 'toolchains/llvm/prebuilt/windows-x86_64/bin'
CC = str(BIN / 'clang.exe')
LIB = ROOT / 'app/src/main/jniLibs/arm64-v8a'
WORK.mkdir(parents=True, exist_ok=True)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def run(argv, **kwargs):
    return subprocess.run([str(a) for a in argv], cwd=WORK, check=True,
                          capture_output=True, **kwargs)

def main():
    archive = ROOT / 'artifacts/native-sources/proot-5.1.107.92.zip'
    assert sha(archive) == '29385d1ddb619a9c4449ab512bfd55032034b22f724ddf98fc95ff300ea32135'
    with zipfile.ZipFile(archive) as source:
        for entry in source.infolist():
            relative = Path(entry.filename)
            assert not relative.is_absolute() and '..' not in relative.parts
        source.extractall(WORK)
    src = WORK / 'proot-5.1.107.92/src'
    patch = ROOT / 'patches/proot-exitkill.patch'
    subprocess.run(['git', 'apply', '--check', str(patch)], cwd=src.parent, check=True)
    subprocess.run(['git', 'apply', str(patch)], cwd=src.parent, check=True)
    extra_patch = ROOT / 'patches/proot-fchmodat2.patch'
    subprocess.run(['git', 'apply', '--check', str(extra_patch)], cwd=src.parent, check=True)
    subprocess.run(['git', 'apply', str(extra_patch)], cwd=src.parent, check=True)
    headers = WORK / 'public-include'
    headers.mkdir(exist_ok=True)
    for name, digest in [
        ('talloc-2.4.3.tar.gz', 'dc46c40b9f46bb34dd97fe41f548b0e8b247b77a918576733c528e83abd854dd'),
        ('libandroid-shmem-0.7.tar.gz', '1e5ff8459bc0a8c229dd8a94b27d119987e09ef3414331c2b5ebfff20b98e867')]:
        path = ROOT / 'artifacts/native-sources' / name
        assert sha(path) == digest
        with tarfile.open(path) as archive_headers:
            for member in archive_headers:
                basename = Path(member.name).name
                if member.isfile() and basename in {'talloc.h', 'shm.h'}:
                    target = headers / ('sys/shm.h' if basename == 'shm.h' else basename)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(archive_headers.extractfile(member).read())
    pins = json.loads((ROOT / 'evidence/proot-staging.json').read_text())
    for name in ['libtalloc.so', 'libandroid-shmem.so']:
        assert sha(LIB / name) == pins['output_sha256'][name]
    common = ['--target=aarch64-linux-android30', '-O2', '-D_FILE_OFFSET_BITS=64',
              '-D_GNU_SOURCE', '-DARG_MAX=131072', '-DWITH_LIBANDROID_SHMEM',
              '-DVERSION="5.1.107.92-tinyagent.2"', '-DPROOT_UNBUNDLE_LOADER="/unused"',
              '-I' + str(src), '-I' + str(headers)]
    links = ['-L' + str(LIB), '-ltalloc', '-landroid-shmem', '-Wl,-z,noexecstack',
             '-Wl,-z,max-page-size=16384']
    features = []
    for feature in ['process_vm', 'seccomp_filter']:
        try:
            run([CC, *common, src / ('.check_' + feature + '.c'), *links,
                 '-o', WORK / ('check-' + feature)])
            features.append('#define HAVE_' + feature.upper())
        except subprocess.CalledProcessError as error:
            raise RuntimeError('Expected Android feature check failed: ' + feature + '\n' +
                               error.stderr.decode(errors='replace')) from error
    (src / 'build.h').write_text('\n'.join(features) + '\n')
    loader_objects = []
    for name in ['loader.c', 'assembly.S']:
        obj = WORK / (name + '.o')
        run([CC, *common, '-fPIC', '-ffreestanding', '-c', src / 'loader' / name, '-o', obj])
        loader_objects.append(obj)
    loader = WORK / 'libproot_loader.so'
    run([CC, '--target=aarch64-linux-android30', *loader_objects, '-static', '-nostdlib',
         '-Wl,--build-id=none,-Ttext=0x2000000000,--rosegment,-z,noexecstack,-z,max-page-size=16384', '-o', loader])
    symbols = run([BIN / 'llvm-readelf.exe', '-s', loader]).stdout
    info = run([Path('C:/Program Files/Git/usr/bin/awk.exe'), '-f', src / 'loader/loader-info.awk'], input=symbols).stdout
    (src / 'loader/loader-info.c').write_bytes(info)
    makefile = (src / 'GNUmakefile').read_text()
    object_block = makefile.split('OBJECTS +=', 1)[1].split('define define_from_arch.h', 1)[0]
    names = re.findall(r'[\w/-]+\.o', object_block) + ['loader/loader-info.o']
    assert len(names) == len(set(names)) and len(names) > 60
    objects = []
    for name in names:
        obj = WORK / 'objects' / name
        obj.parent.mkdir(parents=True, exist_ok=True)
        # Upstream omits string.h here; supply declarations, not relaxed errors.
        extra = ['-include', 'string.h'] if name == 'extension/ashmem_memfd/ashmem_memfd.o' else []
        run([CC, *common, *extra, '-c', src / name.replace('.o', '.c'), '-o', obj])
        objects.append(obj)
    binary = WORK / 'libproot.so'
    run([CC, '--target=aarch64-linux-android30', *objects, *links, '-o', binary])
    for path in [binary, loader]:
        run([BIN / 'llvm-strip.exe', path])
        assert path.read_bytes()[:4] == b'\x7fELF'
    dynamic = run([BIN / 'llvm-readelf.exe', '-d', binary]).stdout.decode()
    assert '[libtalloc.so]' in dynamic and '[libandroid-shmem.so]' in dynamic
    assert 'libtalloc.so.2' not in dynamic and '(RPATH)' not in dynamic and '(RUNPATH)' not in dynamic
    report = {'source_sha256': sha(archive), 'patch_sha256': sha(patch), 'fchmodat2_patch_sha256': sha(extra_patch),
              'ndk': NDK.name, 'compiler_sha256': sha(Path(CC)),
              'build_script_sha256': sha(Path(__file__)), 'objects': len(objects), 'features': features,
              'dependencies': {n: sha(LIB / n) for n in ['libtalloc.so', 'libandroid-shmem.so']},
              'outputs': {p.name: sha(p) for p in [binary, loader]},
              'status': 'built; device validation pending; APK inputs unchanged'}
    (WORK / 'build.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as error:
        print(error.stderr.decode(errors='replace'))
        raise

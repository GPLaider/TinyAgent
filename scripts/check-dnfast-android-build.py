"""Cross-build isolated before/after Android native candidates; never stage an APK.

Supply the project-pinned NDK archive and its extracted ARM64-host clang. The
output directory must not already exist. A build pass is not device execution.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASELINE = '624159e5853f153c77e95b75ac464abb6587cb5f'
NDK_SHA256 = 'fcc3b0ba65318317899fc296df0c5795d472a0cc3870b6fbf659939c1dde63ca'
FILES = ['native/dnfast-launch.c', 'native/fd-gate/probe.c',
         'native/fd-gate/executor_fd.c', 'native/fd-gate/dnfast_native.h',
         'native/fd-gate/LICENSE']


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def run(command, input=None):
    result = subprocess.run(command, input=input, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=120)
    if result.returncode:
        raise RuntimeError(f'Command failed ({result.returncode}): {command}\n{result.stdout}')
    return result.stdout


def inspect_elf(path):
    data = path.read_bytes()
    if data[:6] != b'\x7fELF\x02\x01':
        raise ValueError('Expected little-endian ELF64')
    elf_type, machine = struct.unpack_from('<HH', data, 16)
    offset = struct.unpack_from('<Q', data, 32)[0]
    entry_size, count = struct.unpack_from('<HH', data, 54)
    if elf_type != 3 or machine != 183 or entry_size != 56:
        raise ValueError('Expected ARM64 PIE program headers')
    interpreter = None
    loads = []
    for index in range(count):
        kind, flags, position, virtual, physical, size, memory, align = struct.unpack_from('<IIQQQQQQ', data, offset + index * entry_size)
        if kind == 3:
            interpreter = data[position:position + size].rstrip(b'\0').decode('ascii')
        if kind == 1:
            if align != 16384 or position % align != virtual % align:
                raise ValueError('Invalid 16KiB LOAD alignment')
            loads.append({'offset': position, 'virtual_address': virtual, 'alignment': align})
    if interpreter != '/system/bin/linker64' or not loads:
        raise ValueError('Expected Android 64-bit interpreter and LOAD segments')
    return {'machine': 'AArch64', 'elf_type': 'DYN', 'interpreter': interpreter,
            'load_segments': loads, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler', required=True, type=Path)
    parser.add_argument('--ndk-archive', required=True, type=Path)
    parser.add_argument('--output-directory', required=True, type=Path)
    parser.add_argument('--baseline', default=BASELINE)
    args = parser.parse_args()
    if args.ndk_archive.stat().st_size != 192051660 or digest(args.ndk_archive) != NDK_SHA256:
        raise ValueError('Pinned NDK archive mismatch')
    compiler = args.compiler.resolve(strict=True)
    baseline = run(['git', '-C', str(ROOT), 'rev-parse', '--verify', args.baseline + '^{commit}']).strip()
    flags = ['--target=aarch64-linux-android30', '-std=c11', '-O2', '-Wall', '-Wextra',
             '-Werror', '-Wl,-z,max-page-size=16384']
    macros = run([str(compiler), '--target=aarch64-linux-android30', '-dM', '-E', '-x', 'c', '-'], input='')
    if '#define __ANDROID__ 1' not in macros or '#define __ANDROID_MIN_SDK_VERSION__ 30' not in macros:
        raise ValueError('Compiler did not select Android API 30')
    output = args.output_directory.resolve()
    output.mkdir(parents=True, exist_ok=False)
    report = {'utc': datetime.now(timezone.utc).isoformat(), 'baseline_commit': baseline,
              'scope': 'Cross-compiled candidates only; no APK staging/install, device execution or Android/PRoot runtime acceptance',
              'toolchain_note': 'Project-pinned third-party ARM64-host NDK rebuild, not a Google-distributed host binary. Archive pin verified; selected compiler hash recorded.',
              'ndk_archive_sha256': NDK_SHA256, 'compiler': str(compiler),
              'compiler_sha256': digest(compiler), 'compiler_version': run([str(compiler), '--version']),
              'flags': flags, 'android_macros': [line for line in macros.splitlines() if '__ANDROID' in line],
              'variants': {}}
    for variant in ['before', 'after']:
        tree = output / variant
        sources = {}
        for name in FILES:
            data = subprocess.check_output(['git', '-C', str(ROOT), 'show', baseline + ':' + name]) if variant == 'before' else (ROOT / name).read_bytes()
            path = tree / 'sources' / name
            path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
            sources[name] = hashlib.sha256(data).hexdigest()
        row = {'source_sha256': sources, 'binaries': {}}
        for source, name in [('native/dnfast-launch.c', 'libdnfastlaunch.so'),
                             ('native/fd-gate/probe.c', 'libfdgate.so')]:
            binary = tree / name
            command = [str(compiler), *flags, str(tree / 'sources' / source), '-o', str(binary)]
            log = run(command)
            row['binaries'][name] = dict(inspect_elf(binary), command=command, compiler_output=log)
        report['variants'][variant] = row
        (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()

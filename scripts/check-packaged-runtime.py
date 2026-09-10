"""Verify names and original compressed bytes in the APK, not just source assets."""
import hashlib
import json
from pathlib import Path
import runpy
import zipfile
import argparse

ROOT = Path(__file__).resolve().parents[1]
PINS = runpy.run_path(str(ROOT / 'scripts/stage-runtime-assets.py'))['PINS']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apk', type=Path, default=ROOT / 'app/build/outputs/apk/debug/app-debug.apk')
    parser.add_argument('--variant', choices=['debug', 'release'], default='debug')
    args = parser.parse_args()
    apk = args.apk
    with zipfile.ZipFile(apk) as archive:
        # This app has ~1,100 entries. Large unused ZIP gaps are stale incremental
        # payloads; a clean package needs well below this 4 MiB metadata allowance.
        overhead = apk.stat().st_size - sum(entry.compress_size for entry in archive.infolist())
        assert 0 <= overhead < 4 * 1024 * 1024, f'APK has {overhead} non-payload bytes; clean rebuild required'
        for name in ('AGENTS.md', 'STOCK.md', 'ADB.md', 'ROOT.md'):
            assert archive.read('assets/' + name) == (ROOT / 'harness' / name).read_bytes()
        print('Packaged fixed harness: versioned bytes verified')
        for name in ('prepare-development.sh', 'prepare-self-build.sh', 'prepare-android-sdk-fedora.py', 'configure-android-sdk-fedora.py'):
            assert archive.read('assets/bootstrap/' + name) == (ROOT / 'scripts' / name).read_bytes(), name
        print('Packaged development bootstrap: 4 versioned scripts verified')
        proot = json.loads((ROOT / 'evidence/proot-staging.json').read_text())
        patched = json.loads((ROOT / 'runtime/proot-exitkill-1.json').read_text())
        native_hashes = {**proot['output_sha256'], **patched['outputs']}
        for name, digest in native_hashes.items():
            assert hashlib.sha256(archive.read('lib/arm64-v8a/' + name)).hexdigest() == digest, name
        print('Packaged PRoot: source-built tracer/loader and 2 pinned dependencies verified')
        for name in ('libdnfastlaunch.so', 'libfdgate.so'):
            if args.variant == 'debug':
                assert archive.read('lib/arm64-v8a/'+name) == (ROOT/'app/src/debug/jniLibs/arm64-v8a'/name).read_bytes(), name
            else:
                assert 'lib/arm64-v8a/'+name not in archive.namelist(), 'Debug-only executable in release'
        if args.variant == 'release':
            assert not any('libproot_candidate' in name for name in archive.namelist()), 'Debug recovery probe in release'
        print('Packaged debug native executable inclusion/exclusion verified for ' + args.variant)
        sources = json.loads((ROOT / 'evidence/native-source-collection.json').read_text())
        notices = [notice for source in sources['sources'] for notice in source['notices']]
        notices.append(sources['additional_license'])
        for notice in notices:
            assert hashlib.sha256(archive.read('assets/licenses/' + notice['file'])).hexdigest() == notice['sha256'], notice['file']
        print(f'Packaged native notices: {len(notices)} source/license hashes verified')
        for name, digest in PINS.items():
            with archive.open('assets/' + name + '.bin') as stream:
                assert hashlib.file_digest(stream, 'sha256').hexdigest() == digest, name
        manifest = json.loads(archive.read('assets/web-ui-manifest.json'))
        assert manifest['version'] == '1.18.29'
        assert set(manifest['files']) == set(manifest['sha256'])
        assert '/index.html' in manifest['files']
        for path, digest in manifest['sha256'].items():
            assert path.startswith('/') and '..' not in path.split('/') and '\\' not in path
            assert hashlib.sha256(archive.read('assets/web-ui' + path)).hexdigest() == digest, path
        assert "connect-src 'self'" in manifest['csp']
        assert "script-src 'self' 'wasm-unsafe-eval' 'sha256-" in manifest['csp']
        print(f"Packaged GUI: {len(manifest['files'])} asset hashes verified")
    print('Packaged runtime: 2 original compressed archives verified')


if __name__ == '__main__':
    main()

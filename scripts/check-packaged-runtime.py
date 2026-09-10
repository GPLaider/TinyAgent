"""Verify names and original compressed bytes in the APK, not just source assets."""
import hashlib
import json
from pathlib import Path
import runpy
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PINS = runpy.run_path(str(ROOT / 'scripts/stage-runtime-assets.py'))['PINS']


def main():
    apk = ROOT / 'app/build/outputs/apk/debug/app-debug.apk'
    with zipfile.ZipFile(apk) as archive:
        for name in ('AGENTS.md', 'STOCK.md', 'ADB.md', 'ROOT.md'):
            assert archive.read('assets/' + name) == (ROOT / 'harness' / name).read_bytes()
        print('Packaged fixed harness: versioned bytes verified')
        for name in ('prepare-development.sh', 'prepare-self-build.sh', 'prepare-android-sdk-fedora.py', 'configure-android-sdk-fedora.py'):
            assert archive.read('assets/bootstrap/' + name) == (ROOT / 'scripts' / name).read_bytes(), name
        print('Packaged development bootstrap: 4 versioned scripts verified')
        proot = json.loads((ROOT / 'evidence/proot-staging.json').read_text())
        for name, digest in proot['output_sha256'].items():
            assert hashlib.sha256(archive.read('lib/arm64-v8a/' + name)).hexdigest() == digest, name
        print('Packaged PRoot: 4 native component hashes verified')
        for name in ('libdnfastlaunch.so', 'libfdgate.so'):
            assert archive.read('lib/arm64-v8a/'+name) == (ROOT/'app/src/debug/jniLibs/arm64-v8a'/name).read_bytes(), name
        print('Packaged debug native executables: source build bytes verified')
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

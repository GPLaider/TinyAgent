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
        for name in ('SKILL.md', 'scripts/phone.py'):
            member = 'skills/phone-use/' + name
            assert archive.read('assets/' + member) == (ROOT / 'harness' / member).read_bytes(), member
        print('Packaged phone-use: bundled skill and on-device bridge helper bytes verified')
        dnfast_source = json.loads((ROOT / 'runtime/dnfast-source-export.json').read_text())
        assert hashlib.sha256(archive.read('assets/licenses/' + dnfast_source['notice'])).hexdigest() == dnfast_source['notice_sha256']
        print('Packaged dnfast license: pinned source notice verified')
        cargo_notices = json.loads((ROOT / 'runtime/dnfast-cargo-notices.json').read_text())
        assert hashlib.sha256(archive.read('assets/licenses/dnfast-cargo-notices.tar')).hexdigest() == cargo_notices['archive_sha256']
        print('Packaged dnfast Rust notices: pinned archive verified')
        rpm_notices = json.loads((ROOT / 'runtime/dnfast-rpm-notices.json').read_text())
        for package in rpm_notices['packages']:
            for notice in package['notices']:
                assert hashlib.sha256(archive.read('assets/licenses/dnfast-rpm/' + notice['member'])).hexdigest() == notice['sha256']
        print('Packaged dnfast RPM notices: collected bytes verified')
        source_notices = json.loads((ROOT / 'runtime/dnfast-source-notices.json').read_bytes())
        for notice in source_notices:
            assert hashlib.sha256(archive.read('assets/licenses/' + notice['file'])).hexdigest() == notice['sha256']
        print('Packaged supplemental RPM source notices: ' + str(len(source_notices)))
        supplemental_rpms = {notice['source_rpm'] for notice in source_notices}
        uncovered = [package['package'] for package in rpm_notices['packages']
                     if (package['missing'] or not package['notices'])
                     and package['source_rpm'] not in supplemental_rpms]
        assert not uncovered, f'Packages without packaged RPM or source notices: {uncovered}'
        print(f"Packaged RPM/source notice inventory coverage: {len(rpm_notices['packages'])} packages; not a full license audit")
        for name in ('prepare-development.sh', 'prepare-self-build.sh', 'prepare-android-sdk-fedora.py', 'configure-android-sdk-fedora.py', 'configure-arm-aidl.py', 'tinyagent-packages.py', 'upgrade-dnfast-empty.py', 'upgrade-dnfast-checked.py', 'tinyagent-android.py', 'android-job.sh'):
            assert archive.read('assets/bootstrap/' + name) == (ROOT / 'scripts' / name).read_bytes(), name
        print('Packaged development bootstrap: 10 versioned scripts verified')
        proot = json.loads((ROOT / 'evidence/proot-staging.json').read_text())
        patched = json.loads((ROOT / 'runtime/proot-fchmodat2-2.json').read_text())
        native_hashes = {**proot['output_sha256'], **patched['outputs']}
        for name, digest in native_hashes.items():
            assert hashlib.sha256(archive.read('lib/arm64-v8a/' + name)).hexdigest() == digest, name
        print('Packaged PRoot: source-built tracer/loader and 2 pinned dependencies verified')
        assert archive.read('lib/arm64-v8a/libdnfastlaunch.so') == (ROOT/'app/src/main/jniLibs/arm64-v8a/libdnfastlaunch.so').read_bytes()
        manifest_bytes = (ROOT/'runtime/dnfast-1449710-manifest.json').read_bytes()
        assert archive.read('assets/dnfast-manifest.json') == manifest_bytes
        assert hashlib.sha256(archive.read('assets/dnfast-root-overlay.tar.gz.bin')).hexdigest() == json.loads(manifest_bytes)['overlay_sha256']
        print('Packaged dnfast launcher and pinned overlay verified')
        for name in ('libfdgate.so', 'libmemfdprobe.so'):
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
        print('Packaged runtime: 2 pinned compressed archives verified')


if __name__ == '__main__':
    main()

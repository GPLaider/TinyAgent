"""Measure upgrade buffer lifetimes in disposable roots; no installed root writes.

Uses the pinned 1449710 overlay and two real 43b0928 executables as synthetic old
inputs. Only the child fixture's OLD admission hashes are replaced: this is not
authorization or validation of a production 43b0928-to-1449710 migration.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import statistics
import subprocess
import sys
import tarfile
import tempfile
import time
import zipfile

ROOT = Path(__file__).resolve().parents[2]
BASELINE = '624159e5853f153c77e95b75ac464abb6587cb5f'
SOURCE = 'scripts/upgrade-dnfast-empty.py'
IDENTITY = 'a' * 64
DRIVER = '''import importlib.util,json,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location('upgrade_fixture',sys.argv[1])
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
module.OLD=json.loads(Path(sys.argv[4]).read_text())
module.upgrade(Path(sys.argv[2]),Path(sys.argv[3]))
'''


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', default=BASELINE)
    parser.add_argument('--trials', type=int, default=7)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.trials < 3:
        parser.error('Use at least 3 alternating trials')
    if platform.system() != 'Linux' or not Path('/usr/bin/time').is_file():
        parser.error('Linux and GNU /usr/bin/time required')
    revision = subprocess.check_output(['git', 'rev-parse', '--verify', args.baseline + '^{commit}'], cwd=ROOT, text=True).strip()
    sources = {'before': subprocess.check_output(['git', 'show', revision + ':' + SOURCE], cwd=ROOT),
               'after': (ROOT / SOURCE).read_bytes()}
    runtime = ROOT / 'runtime'
    manifest_path = runtime / 'dnfast-1449710-manifest.json'
    if digest(manifest_path) != 'ec8599eb4b44266abbbcafa0952a67d29d96d4ff5572566ad403c0c425492699':
        raise ValueError('Pinned new manifest mismatch')
    manifest = json.loads(manifest_path.read_text())
    new_overlay = runtime / 'dnfast-1449710-root-overlay.tar.gz'
    if digest(new_overlay) != manifest['overlay_sha256']:
        raise ValueError('New overlay mismatch')
    old_manifest = json.loads((runtime / 'dnfast-43b0928-manifest.json').read_text())
    old_overlay = runtime / 'dnfast-43b0928-root-overlay.tar.gz'
    if digest(old_overlay) != old_manifest['overlay_sha256']:
        raise ValueError('Old fixture overlay mismatch')
    with tarfile.open(old_overlay) as archive:
        old = {name: archive.extractfile(name).read() for name in ['usr/bin/dnfast', 'usr/libexec/dnfast-executor']}
    old_hashes = {name: hashlib.sha256(data).hexdigest() for name, data in old.items()}
    if any(value != old_manifest['files'][name] for name, value in old_hashes.items()):
        raise ValueError('Old fixture member mismatch')
    report = {'scope': __doc__, 'utc': datetime.now(timezone.utc).isoformat(),
              'host': platform.platform(), 'python': sys.version, 'baseline_commit': revision,
              'source_sha256': {name: hashlib.sha256(data).hexdigest() for name, data in sources.items()},
              'new_overlay_sha256': manifest['overlay_sha256'], 'old_overlay_sha256': old_manifest['overlay_sha256'],
              'synthetic_old_hashes': old_hashes, 'trials': [],
              'measurement': 'Fresh disposable fixture per trial, warm inputs/page cache, alternating order. Wall time includes Python and GNU time startup. Child RSS measured by GNU time excludes the outer Python runner. No Android/PRoot or cold-storage claim.'}
    with tempfile.TemporaryDirectory(prefix='dnfast-upgrade-bench-') as temporary:
        base = Path(temporary)
        report['fixture_filesystem'] = subprocess.check_output(['stat', '-f', '-c', '%T', str(base)], text=True).strip()
        driver = base / 'driver.py'; driver.write_text(DRIVER)
        hashes = base / 'old-hashes.json'; hashes.write_text(json.dumps(old_hashes))
        apk = base / 'fixture.apk'
        with zipfile.ZipFile(apk, 'w') as package:
            package.write(manifest_path, 'assets/dnfast-manifest.json')
            package.write(new_overlay, 'assets/dnfast-root-overlay.tar.gz.bin')
        for name, data in sources.items():
            (base / (name + '.py')).write_bytes(data)
        # Trial zero is an excluded warmup; every trial starts from old executables.
        for trial in range(args.trials + 1):
            for variant in (['before', 'after'] if trial % 2 == 0 else ['after', 'before']):
                fixture = base / (variant + '-' + str(trial))
                fixture.mkdir(mode=0o700)
                identity = fixture / '.tinyagent-root-id'
                identity.write_text(IDENTITY); identity.chmod(0o600)
                (fixture / 'var/lib/dnfast/app-proot' / IDENTITY).mkdir(parents=True, mode=0o700)
                for name, data in old.items():
                    target = fixture / name
                    target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
                usage_path = base / 'usage.json'
                usage_path.unlink(missing_ok=True)
                command = ['/usr/bin/time', '--quiet', '--format={"maxrss_KiB":%M,"filesystem_inputs":%I,"filesystem_outputs":%O}',
                           '--output=' + str(usage_path), sys.executable, '-B', '-I', str(driver),
                           str(base / (variant + '.py')), str(fixture), str(apk), str(hashes)]
                started = time.monotonic_ns()
                child = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
                timeout = False
                try:
                    output, _ = child.communicate(timeout=60)
                except subprocess.TimeoutExpired:
                    timeout = True
                    os.killpg(child.pid, signal.SIGKILL)
                    output, _ = child.communicate()
                row = {'variant': variant, 'trial': trial, 'seconds': (time.monotonic_ns() - started) / 1e9,
                       'exit': child.returncode, 'timeout': timeout, 'output': output.decode(errors='replace')}
                if child.returncode == 0 and not timeout:
                    row.update(json.loads(usage_path.read_text()))
                    # Validation is outside the timed interval and checks all published bytes.
                    row['files_verified'] = all(digest(fixture / name) == expected for name, expected in manifest['files'].items())
                    backup = fixture / 'var/lib/dnfast-upgrades/16c6887-to-1449710' / IDENTITY
                    row['backups_verified'] = all(digest(backup / name.replace('/', '_')) == expected for name, expected in old_hashes.items())
                    row['identity_preserved'] = identity.read_text() == IDENTITY
                report['trials'].append(row)
                args.output.write_text(json.dumps(report, indent=2) + '\n')
                if (row['exit'] or timeout or not all(row.get(k) for k in
                        ['files_verified', 'backups_verified', 'identity_preserved'])):
                    raise SystemExit('Upgrade fixture failed; raw result preserved')
        report['summary'] = []
        for variant in sources:
            rows = [r for r in report['trials'] if r['variant'] == variant and r['trial'] > 0]
            report['summary'].append({'variant': variant, 'trials': len(rows),
                'median_seconds': statistics.median(r['seconds'] for r in rows),
                'median_maxrss_KiB': statistics.median(r['maxrss_KiB'] for r in rows),
                'min_seconds': min(r['seconds'] for r in rows), 'max_seconds': max(r['seconds'] for r in rows)})
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report['summary'], indent=2))


if __name__ == '__main__':
    main()

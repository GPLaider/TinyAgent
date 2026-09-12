"""A/B actual overlay validation/staging in temporary trees, using pinned inputs.

Linux ru_maxrss is recorded per child. Inputs/page cache are warm; each trial
starts a new Python process. All produced assets are checked byte-for-byte.
No APK installation, phone, RPMDB or repository asset writes are performed.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import tempfile
import time
import zipfile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = 'scripts/stage-dnfast-runtime.py'
BASELINE = '624159e5853f153c77e95b75ac464abb6587cb5f'


def measured(command):
    with tempfile.TemporaryFile() as log:
        start = time.monotonic_ns()
        child = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        _, status, usage = os.wait4(child.pid, 0)
        child.returncode = os.waitstatus_to_exitcode(status)
        elapsed = time.monotonic_ns() - start
        log.seek(0)
        return {'seconds': elapsed / 1e9, 'maxrss_KiB': usage.ru_maxrss,
                'exit': child.returncode, 'log': log.read().decode(errors='replace')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', default=BASELINE)
    parser.add_argument('--trials', type=int, default=7)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.trials < 3:
        parser.error('Use at least 3 alternating trials')
    revision = subprocess.check_output(['git', 'rev-parse', '--verify', args.baseline + '^{commit}'], cwd=ROOT, text=True).strip()
    before = subprocess.check_output(['git', 'show', revision + ':' + SOURCE], cwd=ROOT)
    after = (ROOT / SOURCE).read_bytes()
    names = {'dnfast-manifest.json': 'dnfast-1449710-manifest.json',
             'dnfast-root-overlay.tar.gz.bin': 'dnfast-1449710-root-overlay.tar.gz'}
    expected = {name: hashlib.sha256((ROOT / 'runtime' / source).read_bytes()).hexdigest()
                for name, source in names.items()}
    report = {'scope': __doc__, 'utc': datetime.now(timezone.utc).isoformat(),
              'host': platform.platform(), 'python': sys.version,
              'baseline_commit': revision, 'input_sha256': expected,
              'source_sha256': {label: hashlib.sha256(source).hexdigest()
                                for label, source in [('before', before), ('after', after)]},
              'tests': {}, 'trials': [], 'summary': []}
    with tempfile.TemporaryDirectory(prefix='dnfast-stage-bench-') as temporary:
        base = Path(temporary)
        apk = base / 'inputs.apk'
        with zipfile.ZipFile(apk, 'w') as package:
            for name, source in names.items():
                package.write(ROOT / 'runtime' / source, 'assets/' + name)
        commands = {}
        for label, source in [('before', before), ('after', after)]:
            tree = base / label
            (tree / 'scripts').mkdir(parents=True)
            (tree / 'runtime').mkdir()
            script = tree / SOURCE
            script.write_bytes(source)
            for name in names.values():
                (tree / 'runtime' / name).symlink_to(ROOT / 'runtime' / name)
            commands[label] = [sys.executable, '-I', str(script)]

        def verify(label):
            assets = base / label / 'app/src/main/assets'
            assert {path.name for path in assets.iterdir()} == set(expected)
            for name, digest in expected.items():
                with (assets / name).open('rb') as stream:
                    assert hashlib.file_digest(stream, 'sha256').hexdigest() == digest

        for label in commands:
            for extra in [[], ['--installed-apk', str(apk)]]:
                result = measured(commands[label] + extra)
                assert result['exit'] == 0, result
                verify(label)
            for damaged in names:
                bad = base / 'bad.apk'
                with zipfile.ZipFile(bad, 'w') as package:
                    for name, source in names.items():
                        if name == damaged:
                            package.writestr('assets/' + name, b'corrupt')
                        else:
                            package.write(ROOT / 'runtime' / source, 'assets/' + name)
                result = measured(commands[label] + ['--installed-apk', str(bad)])
                assert result['exit'] != 0 and 'hash mismatch' in result['log'], result
                verify(label)
            report['tests'][label] = 'PASS direct and installed-APK byte-exact staging; corrupt manifest/overlay rejected and previous assets preserved'
        for trial in range(args.trials):
            for label in (['before', 'after'] if trial % 2 == 0 else ['after', 'before']):
                row = measured(commands[label])
                assert row['exit'] == 0, row
                verify(label)
                report['trials'].append(dict(row, variant=label, trial=trial))
        for label in commands:
            rows = [row for row in report['trials'] if row['variant'] == label]
            report['summary'].append({'variant': label,
                'median_seconds': statistics.median(row['seconds'] for row in rows),
                'median_maxrss_KiB': statistics.median(row['maxrss_KiB'] for row in rows),
                'min_seconds': min(row['seconds'] for row in rows),
                'max_seconds': max(row['seconds'] for row in rows)})
    encoded = json.dumps(report, indent=2) + '\n'
    if args.output:
        args.output.write_text(encoded)
        print(json.dumps({'tests': report['tests'], 'summary': report['summary']}, indent=2))
    else:
        print(encoded, end='')


if __name__ == '__main__':
    main()

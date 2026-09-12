"""A/B real launcher state-directory I/O on a chosen disposable filesystem.

Both variants retain five fsync calls. First creation and warm traversal are
reported separately; no Android label, PRoot, full CLI or crash-durability claim.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import shutil
import statistics
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
BASELINE = '624159e5853f153c77e95b75ac464abb6587cb5f'
SOURCE = 'native/dnfast-launch.c'


def run(command):
    return subprocess.check_output(command, text=True, stderr=subprocess.STDOUT, timeout=60)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', default=BASELINE)
    parser.add_argument('--fixture-parent', type=Path, default=Path(tempfile.gettempdir()))
    parser.add_argument('--trials', type=int, default=9)
    parser.add_argument('--cc', default='cc')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.trials < 3:
        parser.error('Use at least 3 alternating trials')
    revision = run(['git', '-C', str(ROOT), 'rev-parse', '--verify', args.baseline + '^{commit}']).strip()
    before = subprocess.check_output(['git', '-C', str(ROOT), 'show', revision + ':' + SOURCE])
    sources = {'before': before, 'after': (ROOT / SOURCE).read_bytes()}
    report = {'scope': __doc__, 'utc': datetime.now(timezone.utc).isoformat(),
              'host': platform.platform(), 'baseline_commit': revision,
              'compiler': run([args.cc, '--version']).splitlines()[0],
              'source_sha256': {name: hashlib.sha256(data).hexdigest() for name, data in sources.items()},
              'fixture_parent': str(args.fixture_parent.resolve()),
              'tests': {}, 'trials': [], 'summary': []}
    with tempfile.TemporaryDirectory(prefix='dnfast-launcher-state-', dir=args.fixture_parent) as temporary:
        base = Path(temporary)
        report['filesystem'] = run(['stat', '-f', '-c', '%T', str(base)]).strip()
        binaries = {}
        for variant, source in sources.items():
            path = base / (variant + '.c'); path.write_bytes(source)
            common = [args.cc, '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                      '-DLAUNCHER_SOURCE="' + str(path) + '"']
            test = base / (variant + '-test')
            run(common + [str(ROOT / 'native/dnfast-launch-test.c'), '-o', str(test)])
            result = run([str(test)])
            report['tests'][variant] = result
            fixture = Path(result.strip().split('fixture=')[-1])
            assert fixture.parent == Path('/tmp') and fixture.name.startswith('tinyagent-launch-test-')
            shutil.rmtree(fixture)
            binary = base / variant
            run(common + [str(Path(__file__).with_name('launcher-state.c')), '-o', str(binary)])
            binaries[variant] = binary
        for mode in ['first', 'warm']:
            for trial in range(args.trials):
                for variant in (['before', 'after'] if trial % 2 == 0 else ['after', 'before']):
                    fixture = base / f'{mode}-{trial}-{variant}'
                    fixture.mkdir(mode=0o700)
                    row = json.loads(run([str(binaries[variant]), str(fixture), mode, '500' if mode == 'warm' else '1']))
                    row.update(variant=variant, mode=mode, trial=trial)
                    if row['fsync_per_traversal'] != 5:
                        raise RuntimeError('Durability syscall count changed')
                    report['trials'].append(row)
                    args.output.write_text(json.dumps(report, indent=2) + '\n')
                    shutil.rmtree(fixture)
            for variant in sources:
                rows = [r for r in report['trials'] if r['variant'] == variant and r['mode'] == mode]
                values = [r['ns_per_traversal'] for r in rows]
                report['summary'].append({'variant': variant, 'mode': mode,
                    'median_ns': statistics.median(values), 'min_ns': min(values), 'max_ns': max(values),
                    'mkdirat_per_traversal': rows[0]['mkdirat_per_traversal'], 'fsync_per_traversal': rows[0]['fsync_per_traversal']})
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'filesystem': report['filesystem'], 'tests': report['tests'], 'summary': report['summary']}, indent=2))


if __name__ == '__main__':
    main()

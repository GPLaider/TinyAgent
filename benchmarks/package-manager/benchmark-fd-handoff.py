"""Rootless Linux FD handoff A/B test; no RPM, phone, APK or user-root writes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import statistics
import subprocess
import tempfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
SOURCE = 'native/fd-gate/executor_fd.c'
BASELINE = '624159e5853f153c77e95b75ac464abb6587cb5f'


def run(argv):
    return subprocess.check_output(argv, cwd=ROOT, text=True, stderr=subprocess.STDOUT, timeout=120)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', default=BASELINE, help='Git revision containing the original source')
    parser.add_argument('--cc', default='cc')
    parser.add_argument('--trials', type=int, default=9)
    parser.add_argument('--output', type=Path, help='Save JSON; defaults to stdout')
    args = parser.parse_args()
    if args.trials < 3:
        parser.error('Use at least 3 alternating trials')
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    if soft < 8192:
        if hard != resource.RLIM_INFINITY and hard < 8192:
            parser.error('Tests require RLIMIT_NOFILE >= 8192 (1024 artifacts and sentinel FD4096)')
        resource.setrlimit(resource.RLIMIT_NOFILE, (8192, hard))
    revision = run(['git', 'rev-parse', '--verify', args.baseline + '^{commit}']).strip()
    before = run(['git', 'show', revision + ':' + SOURCE])
    after = (ROOT / SOURCE).read_text()
    report = {
        'scope': 'Warm host compact FD setup, not complete dnfast execution, Android/PRoot, download or solve performance. euid gate and final exec destination intercepted; regression controls also perform real exec.',
        'utc': datetime.now(timezone.utc).isoformat(),
        'host': platform.platform(), 'uid': os.getuid(),
        'cpu_count': os.cpu_count(), 'affinity': sorted(os.sched_getaffinity(0)),
        'compiler': run([args.cc, '--version']).splitlines()[0],
        'compiler_flags': ['-std=c11', '-O2', '-Wall', '-Wextra', '-Werror'],
        'harness_sha256': hashlib.sha256(Path(__file__).with_name('fd-handoff.c').read_bytes()).hexdigest(),
        'baseline_commit': revision,
        'sha256': {name: hashlib.sha256(data.encode()).hexdigest()
                   for name, data in [('before', before), ('after', after)]},
        'tests': {}, 'trials': [], 'summary': [],
    }
    with tempfile.TemporaryDirectory(prefix='dnfast-fd-bench-') as temporary:
        directory = Path(temporary)
        binaries = {}
        for label, source in [('before', before), ('after', after)]:
            path = directory / (label + '.c')
            path.write_text(source)
            executable = directory / label
            command = [args.cc, '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                       '-I' + str(ROOT / 'native/fd-gate'),
                       '-DEXECUTOR_SOURCE="' + str(path) + '"',
                       str(Path(__file__).with_name('fd-handoff.c')), '-o', str(executable)]
            run(command)
            report['tests'][label] = run([str(executable), '--test']).strip()
            binaries[label] = executable
        for count in [0, 1, 16, 256, 1024]:
            iterations = max(100, 20000 // (count + 2))
            for trial in range(args.trials):
                order = ['before', 'after'] if trial % 2 == 0 else ['after', 'before']
                for label in order:
                    row = json.loads(run([str(binaries[label]), '--bench', str(count), str(iterations)]))
                    report['trials'].append(dict(row, variant=label, trial=trial))
            medians = {}
            for label in binaries:
                rows = [row for row in report['trials'] if row['artifacts'] == count and row['variant'] == label]
                values = [row['ns_per_handoff'] for row in rows]
                medians[label] = statistics.median(values)
                report['summary'].append({
                    'artifacts': count, 'variant': label,
                    'median_ns': medians[label], 'min_ns': min(values), 'max_ns': max(values),
                    'fcntl_per_handoff': rows[0]['fcntl_per_handoff'],
                    'dup3_per_handoff': rows[0]['dup3_per_handoff'],
                })
            report['summary'][-1]['median_speedup'] = medians['before'] / medians['after']
    encoded = json.dumps(report, indent=2) + '\n'
    if args.output:
        args.output.write_text(encoded)
        print(json.dumps({'tests': report['tests'], 'summary': report['summary']}, indent=2))
    else:
        print(encoded, end='')


if __name__ == '__main__':
    main()

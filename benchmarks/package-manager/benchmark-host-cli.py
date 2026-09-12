"""Compare pinned dnfast and installed dnf5 --help startup on an ARM64 Linux host.

This is a warm-cache CLI startup comparison, not Android/PRoot, solver, download,
RPM transaction or package-policy parity. No package manager mutation is invoked.
The exact shipped dnfast overlay is verified and unpacked into a temporary tree.
Both commands use explicit ELF loaders and the same isolated HOME/environment.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import signal
import statistics
import subprocess
import tarfile
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = 'ec8599eb4b44266abbbcafa0952a67d29d96d4ff5572566ad403c0c425492699'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def unpack(destination):
    manifest_path = ROOT / 'runtime/dnfast-1449710-manifest.json'
    if digest(manifest_path) != MANIFEST:
        raise ValueError('Pinned dnfast manifest mismatch')
    manifest = json.loads(manifest_path.read_text())
    overlay = ROOT / 'runtime/dnfast-1449710-root-overlay.tar.gz'
    if digest(overlay) != manifest['overlay_sha256']:
        raise ValueError('Pinned dnfast overlay mismatch')
    found = set()
    with tarfile.open(overlay) as archive:
        for member in archive:
            name = PurePosixPath(member.name)
            if (not member.isfile() or name.is_absolute() or '..' in name.parts or
                    member.name not in manifest['files'] or member.name in found):
                raise ValueError('Unexpected overlay member: ' + member.name)
            target = destination / member.name
            target.parent.mkdir(parents=True, exist_ok=True)
            hasher = hashlib.sha256()
            with archive.extractfile(member) as source, target.open('xb') as output:
                while chunk := source.read(256 * 1024):
                    hasher.update(chunk)
                    output.write(chunk)
            if hasher.hexdigest() != manifest['files'][member.name]:
                raise ValueError('Pinned member mismatch: ' + member.name)
            target.chmod(0o755)
            found.add(member.name)
    if found != set(manifest['files']):
        raise ValueError('Incomplete overlay')
    return manifest


def measure(command, cwd, env, timeout):
    """Blocking wait4 avoids a polling floor; SIGALRM bounds a stalled child."""
    def expired(signum, frame):
        raise TimeoutError('CLI deadline expired')
    with tempfile.TemporaryFile() as output:
        started = time.monotonic_ns()
        child = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                 stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
        old_handler = signal.signal(signal.SIGALRM, expired)
        timed_out = False
        try:
            signal.setitimer(signal.ITIMER_REAL, timeout)
            try:
                _, status, usage = os.wait4(child.pid, 0)
            except TimeoutError:
                timed_out = True
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                _, status, usage = os.wait4(child.pid, 0)
            child.returncode = os.waitstatus_to_exitcode(status)
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old_handler)
            if child.returncode is None:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                child.wait()
        elapsed = (time.monotonic_ns() - started) / 1e9
        output.seek(0)
        data = output.read()
    # This peak includes Python's pre-exec child image; do not use it as CLI RSS.
    return {'seconds': elapsed, 'launcher_maxrss_KiB': usage.ru_maxrss,
            'user_seconds': usage.ru_utime, 'system_seconds': usage.ru_stime,
            'exit': child.returncode, 'timeout': timed_out,
            'output_sha256': hashlib.sha256(data).hexdigest()}, data.decode(errors='replace')


def valid_help(tool, output):
    if tool == 'dnfast':
        try:
            record = json.loads(output)
        except (ValueError, TypeError):
            return False
        return (isinstance(record, dict) and record.get('schema') == 'dnfast.cli.v1' and
                record.get('command') == 'cli' and record.get('exit_code') == 0 and
                record.get('errors') == [] and isinstance(record.get('message'), str) and
                'Usage: dnfast' in record['message'] and 'Commands:' in record['message'])
    return 'Usage:' in output and 'dnf5' in output and 'Commands:' in output


def summarize(rows, trials):
    result = []
    for tool in ['dnfast', 'dnf5']:
        measured = [row for row in rows if row['tool'] == tool and row['trial'] > 0]
        failures = [row for row in measured if row['exit'] or row['timeout'] or not row['valid_help']]
        complete = (len(measured) == trials and
                    {row['trial'] for row in measured} == set(range(1, trials + 1)))
        status = 'failed' if failures else 'passed' if complete else 'incomplete'
        result.append({'tool': tool, 'status': status, 'measured_runs': len(measured),
                       'failed_runs': len(failures),
                       'median_seconds': statistics.median(row['seconds'] for row in measured) if status == 'passed' else None})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trials', type=int, default=15, help='Measured runs per tool, plus one warmup')
    parser.add_argument('--dnf5', type=Path, default=Path('/usr/bin/dnf5'))
    parser.add_argument('--system-loader', type=Path, default=Path('/lib/ld-linux-aarch64.so.1'))
    parser.add_argument('--timeout', type=float, default=10)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if platform.system() != 'Linux' or platform.machine() != 'aarch64':
        parser.error('Pinned runtime requires ARM64 Linux; Android/PRoot is not supported by this host harness')
    if args.trials < 3 or not 0 < args.timeout <= 60:
        parser.error('Use at least 3 trials and a timeout in (0, 60] seconds')
    if not Path('/usr/bin/time').is_file():
        parser.error('GNU /usr/bin/time is required for separate child RSS measurements')
    report = {'scope': __doc__, 'utc': datetime.now(timezone.utc).isoformat(),
              'host': platform.platform(), 'python': platform.python_version(),
              'cpu_count': os.cpu_count(), 'affinity': sorted(os.sched_getaffinity(0)),
              'uid': os.getuid(), 'versions': {}, 'outputs': {}, 'trials': [], 'rss_trials': [],
              'rss_method': 'Separate GNU time child ru_maxrss samples. Direct Python wait4 peak includes the pre-exec Python image and is retained only as launcher_maxrss_KiB. GNU time wrapper elapsed is excluded from CLI timing medians.'}
    with tempfile.TemporaryDirectory(prefix='dnfast-cli-bench-') as temporary:
        base = Path(temporary)
        runtime = base / 'runtime'
        manifest = unpack(runtime)
        home = base / 'home'
        home.mkdir()
        env = {'PATH': '/usr/bin:/bin', 'HOME': str(home), 'LC_ALL': 'C', 'LANG': 'C',
               'TERM': 'dumb', 'XDG_CACHE_HOME': str(home / '.cache'),
               'XDG_CONFIG_HOME': str(home / '.config')}
        lib = runtime / manifest['library_prefix'].lstrip('/')
        binary = runtime / 'usr/bin/dnfast'
        dnf5 = args.dnf5.resolve(strict=True)
        loader = args.system_loader.resolve(strict=True)
        commands = {'dnfast': [str(lib / 'ld-linux-aarch64.so.1'), '--library-path', str(lib), str(binary)],
                    'dnf5': [str(loader), str(dnf5)]}
        report.update({'manifest_sha256': MANIFEST, 'source_commit': manifest['source_commit'],
                       'overlay_sha256': manifest['overlay_sha256'], 'commands': commands,
                       'environment': env, 'verified_overlay_members': len(manifest['files']),
                       'binary_sha256': {'dnfast': digest(binary), 'dnf5': digest(dnf5)},
                       'loader_sha256': {'dnfast': digest(lib / 'ld-linux-aarch64.so.1'), 'dnf5': digest(loader)},
                       'dnf5_library_listing': subprocess.run(['ldd', str(dnf5)], capture_output=True, text=True, timeout=10).stdout})
        for tool, command in commands.items():
            row, output = measure(command + ['--version'], home, env, args.timeout)
            report['versions'][tool] = dict(row, output=output)
        for trial in range(args.trials + 1):
            order = ['dnfast', 'dnf5'] if trial % 2 == 0 else ['dnf5', 'dnfast']
            for tool in order:
                row, output = measure(commands[tool] + ['--help'], home, env, args.timeout)
                row.update(tool=tool, trial=trial, valid_help=valid_help(tool, output))
                report['outputs'][row['output_sha256']] = output
                report['trials'].append(row)
                report['summary'] = summarize(report['trials'], args.trials)
                args.output.write_text(json.dumps(report, indent=2) + '\n')
        # Measure RSS separately, after direct timing, with a small native parent.
        # No GNU time launch overhead is mixed into headline elapsed time.
        for trial in range(1, args.trials + 1):
            for tool in (['dnfast', 'dnf5'] if trial % 2 else ['dnf5', 'dnfast']):
                rss_path = base / 'child-rss.txt'
                rss_path.unlink(missing_ok=True)
                command = ['/usr/bin/time', '--quiet', '--format=%M', '--output=' + str(rss_path),
                           *commands[tool], '--help']
                row, output = measure(command, home, env, args.timeout)
                rss = rss_path.read_text().strip() if rss_path.exists() else ''
                row.update(tool=tool, trial=trial, valid_help=valid_help(tool, output),
                           child_maxrss_KiB=int(rss) if rss.isdigit() else None)
                report['outputs'][row['output_sha256']] = output
                report['rss_trials'].append(row)
                args.output.write_text(json.dumps(report, indent=2) + '\n')
        for summary in report['summary']:
            rows = [row for row in report['rss_trials'] if row['tool'] == summary['tool']]
            valid = all(not row['exit'] and not row['timeout'] and row['valid_help'] and
                        row['child_maxrss_KiB'] is not None for row in rows)
            summary['rss_status'] = 'passed' if valid and len(rows) == args.trials else 'failed'
            summary['median_child_maxrss_KiB'] = statistics.median(row['child_maxrss_KiB'] for row in rows) if summary['rss_status'] == 'passed' else None
        args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report['summary'], indent=2))
    if any(row['status'] != 'passed' or row['rss_status'] != 'passed' for row in report['summary']):
        raise SystemExit(1)


if __name__ == '__main__':
    main()

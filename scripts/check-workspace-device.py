"""Install isolated, signer-verified probes; run real Android FD/Binder checks; remove them.

Only the two absent probe package IDs below are installed/uninstalled. The runner
never updates TinyAgent, grants privileged permissions, reboots or changes data
outside the probe apps. Pass the exact intended serial and certificate digest.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

OWNER = 'io.github.gplaider.tinyagent.workspaceprobe'
CLIENT = OWNER + '.client'
INSTRUMENT = 'io.github.gplaider.tinyagent.WorkspaceDeviceProbe'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial', required=True)
    parser.add_argument('--owner-apk', type=Path, required=True)
    parser.add_argument('--client-apk', type=Path, required=True)
    parser.add_argument('--expected-signer', required=True)
    parser.add_argument('--apksigner-jar', type=Path, required=True)
    parser.add_argument('--aapt2', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--activity-recreate', action='store_true', help='Also exercise the real export Activity during recreation')
    parser.add_argument('--process-death', action='store_true', help='Kill only the stopped isolated owner process and restore its saved task')
    args = parser.parse_args()
    if not re.fullmatch('[0-9a-f]{64}', args.expected_signer):
        parser.error('expected-signer must be a lowercase SHA256 certificate digest')
    java = str(Path(os.environ['JAVA_HOME']) / 'bin/java') if 'JAVA_HOME' in os.environ else 'java'
    report = {'serial': args.serial, 'signer': args.expected_signer, 'artifacts': {}, 'steps': [], 'cleanup': {}}
    root = Path(__file__).resolve().parents[1]
    report['production_sources'] = {
        name: hashlib.sha256((root / 'app/src/main/java/io/github/gplaider/tinyagent' / name).read_bytes()).hexdigest()
        for name in ['WorkspaceFiles.java', 'WorkspaceFileProvider.java', 'WorkspaceCopy.java', 'InstallerActivity.java']
    }
    installed = []

    def run(command, timeout=30, check=True):
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        if check and result.returncode:
            raise RuntimeError(f'{command[:3]} failed: {result.stdout}\n{result.stderr}')
        return result

    def adb(*command, **kwargs):
        return run(['adb', '-s', args.serial, *command], **kwargs)

    def packages():
        return set(adb('shell', 'pm', 'list', 'packages').stdout.splitlines())

    def save():
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')

    try:
        for package, apk in [(OWNER, args.owner_apk), (CLIENT, args.client_apk)]:
            signed = run([java, '-jar', str(args.apksigner_jar), 'verify', '--print-certs', str(apk)]).stdout
            signers = re.findall(r'Signer #\d+ certificate SHA-256 digest: ([0-9a-f]+)', signed)
            if signers != [args.expected_signer]:
                raise RuntimeError(f'{package}: unexpected APK signer {signers}')
            badging = run([str(args.aapt2), 'dump', 'badging', str(apk)]).stdout
            if not re.search(r"^package: name='" + re.escape(package) + "'", badging, re.M):
                raise RuntimeError(f'Unexpected application ID for {apk}')
            report['artifacts'][package] = {'sha256': hashlib.sha256(apk.read_bytes()).hexdigest(), 'signer_output': signed}
        if adb('get-serialno').stdout.strip() != args.serial:
            raise RuntimeError('ADB serial mismatch')
        report['sdk'] = adb('shell', 'getprop', 'ro.build.version.sdk').stdout.strip()
        report['selinux'] = adb('shell', 'getenforce').stdout.strip()
        report['boot_completed'] = adb('shell', 'getprop', 'sys.boot_completed').stdout.strip()
        if report['selinux'] != 'Enforcing' or report['boot_completed'] != '1':
            raise RuntimeError('Expected fully booted Android with SELinux Enforcing')
        initial = packages()
        if any('package:' + p in initial for p in [OWNER, CLIENT]):
            raise RuntimeError('Probe package already exists; refusing to replace or remove user state')
        report['existing_tinyagent_paths'] = {
            p: adb('shell', 'pm', 'path', p).stdout for p in ['io.github.gplaider.tinyagent', 'io.github.gplaider.tinyagent.debug']
        }
        for package, apk in [(OWNER, args.owner_apk), (CLIENT, args.client_apk)]:
            # Record cleanup responsibility before dispatch: transport can fail after installation.
            installed.append(package)
            result = adb('install', '--no-streaming', '-t', str(apk), timeout=60)
            if 'Success' not in result.stdout:
                raise RuntimeError('Installation not confirmed: ' + result.stdout)
        steps = [(OWNER, 'owner'), (CLIENT, 'client-denied'), (CLIENT, 'client-granted'), (CLIENT, 'client-denied')]
        if args.activity_recreate:
            steps.extend([(OWNER, 'activity-recreate'), (OWNER, 'activity-recreate-failure'), (OWNER, 'activity-isolation'), (OWNER, 'activity-dismiss'), (OWNER, 'activity-status-switch')])
            steps.extend((OWNER, 'activity-picker-' + result) for result in ['save', 'cancel', 'null', 'empty'])
        for package, mode in steps:
            result = adb('shell', 'am', 'instrument', '-w', '-r', '-e', 'mode', mode,
                         package + '/' + INSTRUMENT, timeout=60)
            output = result.stdout + result.stderr
            report['steps'].append({'package': package, 'mode': mode, 'output': output})
            save()
            if f'PASS mode={mode}' not in output or 'INSTRUMENTATION_CODE: -1' not in output or 'FAIL ' in output:
                raise RuntimeError('Instrumentation failed: ' + output)
            print(f'PASS {mode}', flush=True)
        if args.process_death:
            def death_instrument(mode, *extra):
                result = adb('shell', 'am', 'instrument', '-w', '-r', '-e', 'mode', mode, *extra,
                             CLIENT + '/' + INSTRUMENT, timeout=60)
                output = result.stdout + result.stderr
                report['steps'].append({'package': CLIENT, 'mode': mode, 'output': output})
                save()
                if f'PASS mode={mode}' not in output or 'INSTRUMENTATION_CODE: -1' not in output or 'FAIL ' in output:
                    raise RuntimeError('Process-death instrumentation failed: ' + output)
                print(f'PASS {mode}', flush=True)
                return output
            for phase in ['running', 'completed-before-save', 'completed-after-save']:
                prepared = death_instrument('death-prepare', '-e', 'phase', phase)
                target = re.search(r'DEATH_TARGET pid=(\d+) task=(\d+)', prepared)
                if target is None:
                    raise RuntimeError('Missing exact probe PID/task')
                pid, task = target.groups()
                if adb('shell', 'pidof', OWNER).stdout.strip() != pid:
                    raise RuntimeError('Probe PID changed before termination')
                adb('shell', 'am', 'kill', OWNER)
                deadline = time.monotonic() + 5
                while True:
                    remaining = adb('shell', 'pidof', OWNER, check=False).stdout.strip()
                    if not remaining:
                        break
                    if time.monotonic() >= deadline:
                        raise RuntimeError('Stopped probe process did not die; no escalation attempted')
                    time.sleep(0.1)
                report.setdefault('process_deaths', []).append({'phase': phase, 'old_pid': int(pid), 'task': int(task), 'owner_pid_absent_before_restore': True})
                save()
                death_instrument('death-restore', '-e', 'oldpid', pid, '-e', 'task', task, '-e', 'phase', phase)
            for result_mode in ['save', 'cancel', 'null', 'empty']:
                death_instrument('death-picker-' + result_mode)
        report['passed'] = True
    except BaseException as error:
        report['passed'] = False
        report['error'] = str(error)
        raise
    finally:
        for package in reversed(installed):
            try:
                result = adb('uninstall', package, timeout=30, check=False)
                remaining = 'package:' + package in packages()
                report['cleanup'][package] = {'output': result.stdout + result.stderr, 'absent': not remaining}
            except Exception as error:
                report['cleanup'][package] = {'error': str(error), 'absent': False}
        if installed:
            try:
                report['tinyagent_paths_unchanged'] = all(
                    adb('shell', 'pm', 'path', p).stdout == before
                    for p, before in report.get('existing_tinyagent_paths', {}).items()
                )
            except Exception as error:
                report['baseline_check_error'] = str(error)
                report['tinyagent_paths_unchanged'] = False
        save()
    if not all(item['absent'] for item in report['cleanup'].values()):
        raise RuntimeError('Probe removal incomplete; inspect report')
    if not report.get('tinyagent_paths_unchanged', False):
        raise RuntimeError('Existing TinyAgent path preservation not verified; inspect report')
    print('PASS isolated probe cleanup; report:', args.report)


if __name__ == '__main__':
    main()

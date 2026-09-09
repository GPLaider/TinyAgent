"""Run PreRoot entrypoint checks on the designated Edge 40, without model calls."""
import hashlib
import json
from pathlib import Path
import subprocess

ADB = Path('C:/Users/Administrator/AppData/Local/Android/Sdk/platform-tools/adb.exe')
REPO = Path(__file__).resolve().parents[1]
TARGET = '100.79.65.42:5555'
ROOT = '/data/local/tmp/tinyagent-compat-20260908'
STAGE = '/data/local/tmp/tinyagent-preroot-0.1.0'


def adb(*args):
    return subprocess.run([str(ADB), '-s', TARGET, *args], capture_output=True,
                          text=True, encoding='utf-8', timeout=45)


def main():
    identity = adb('shell', 'getprop', 'ro.serialno')
    assert identity.returncode == 0 and identity.stdout.strip() == 'ZY22HZPLL8'
    before = adb('shell', 'cat', '/proc/mounts')
    assert before.returncode == 0
    assert adb('shell', 'mkdir', '-p', STAGE).returncode == 0
    hashes = {}
    for name in ('preroot.sh', 'enter.sh'):
        source = REPO / 'preroot' / name
        hashes[name] = hashlib.sha256(source.read_bytes()).hexdigest()
        pushed = adb('push', str(source), f'{STAGE}/{name}')
        assert pushed.returncode == 0, pushed.stderr
    results = []
    cases = [
        ('doctor', 'unrestricted-root', ['doctor'], 0, 'provider=fedora-preroot'),
        ('fedora-id', 'unrestricted-root', ['exec', '/workspace', '/usr/bin/id'], 0, 'uid=0'),
        ('working-directory', 'unrestricted-root', ['exec', '/workspace', '/usr/bin/pwd'], 0, '/workspace'),
        ('backend-binary', 'unrestricted-root', ['exec', '/workspace', '/usr/local/bin/opencode', '--version'], 0, '1.18.29'),
        ('exit-status', 'unrestricted-root', ['exec', '/workspace', '/usr/bin/false'], 1, ''),
        ('missing-directory', 'unrestricted-root', ['exec', '/__tinyagent_missing_directory__', '/usr/bin/true'], 125, ''),
        ('restricted-refused', 'restricted', ['exec', '/workspace', '/usr/bin/id'], 1, ''),
        ('invalid-action', 'unrestricted-root', ['unknown'], 1, ''),
    ]
    for name, mode, args, expected, marker in cases:
        result = adb('shell', '/system/bin/sh', f'{STAGE}/preroot.sh', ROOT, mode, *args)
        passed = result.returncode == expected and marker in result.stdout
        results.append(dict(name=name, passed=passed, exit=result.returncode,
                            stdout=result.stdout, stderr=result.stderr))
        print(name, 'PASS' if passed else 'FAIL', result.returncode, flush=True)
    after = adb('shell', 'cat', '/proc/mounts')
    # Android can change unrelated mounts; our root must not gain global mounts.
    leaked = [line for line in after.stdout.splitlines() if ROOT in line]
    results.append(dict(name='no-global-mounts', passed=after.returncode == 0 and not leaked))
    output = REPO / 'evidence' / 'preroot-entrypoint.json'
    output.write_text(json.dumps(dict(serial=identity.stdout.strip(), root=ROOT,
                                     sha256=hashes, results=results), indent=2) + '\n', encoding='utf-8')
    assert all(item['passed'] for item in results), str(output)


if __name__ == '__main__':
    main()

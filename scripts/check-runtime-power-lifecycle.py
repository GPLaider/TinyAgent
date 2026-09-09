"""Lyriq2 only: service stop releases its CPU lock; restart reacquires it."""
import json
from pathlib import Path
import subprocess
import time

ADB = Path.home() / 'AppData/Local/Android/Sdk/platform-tools/adb.exe'
SERIAL = '100.79.65.42:5555'
PACKAGE = 'io.github.gplaider.tinyagent.debug'
SERVICE = PACKAGE + '/io.github.gplaider.tinyagent.RuntimeSetupService'


def adb(*args):
    return subprocess.check_output([str(ADB), '-s', SERIAL, *args], timeout=30).decode().strip()


def locks():
    return [line.strip() for line in adb('shell', 'dumpsys', 'power').splitlines()
            if 'PARTIAL_WAKE_LOCK' in line and "'TinyAgent:LocalRuntime'" in line]


def wait_lock(present):
    for _ in range(30):
        current = locks()
        if bool(current) == present:
            return current
        time.sleep(1)
    raise AssertionError(f'Runtime lock presence did not become {present}')


assert adb('shell', 'getprop', 'ro.serialno') == 'ZY22HZPLL8'
apk = adb('shell', 'pm', 'path', PACKAGE).removeprefix('package:')
result = {'serial': SERIAL, 'apk_sha256': adb('shell', 'sha256sum', apk).split()[0]}
result['before'] = wait_lock(True)
assert all('uid=10151 ' in line for line in result['before'])
try:
    adb('shell', 'am', 'startservice', '-n', SERVICE, '-a', 'io.github.gplaider.tinyagent.STOP_BACKEND')
    result['after_stop'] = wait_lock(False)
    time.sleep(2)
    owned = [line for line in adb('shell', 'ps', '-A', '-o', 'UID,NAME').splitlines()
             if line.split()[:1] == ['10151'] and line.split()[-1] in ('libproot.so', 'opencode')]
    assert not owned, owned
    result['backend_processes_after_stop'] = owned
finally:
    adb('shell', 'am', 'start-foreground-service', '-n', SERVICE)
result['after_restart'] = wait_lock(True)
result['stay_on_while_plugged_in'] = adb('shell', 'settings', 'get', 'global', 'stay_on_while_plugged_in')
assert result['stay_on_while_plugged_in'] == '0'
Path('evidence/runtime-power-lifecycle.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('PASS: app UID lock released, backend stopped, service restarted, lock reacquired; stay-on=0')

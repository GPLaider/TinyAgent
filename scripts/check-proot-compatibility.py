"""Verify actual app-owned PRoot environments without printing backend secrets."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ADB = Path.home()/'AppData/Local/Android/Sdk/platform-tools/adb.exe'
SERIAL = '000501423003390'
PACKAGE = 'io.github.gplaider.tinyagent.debug'
def adb(*args):
    return subprocess.check_output([str(ADB),'-s',SERIAL,*args],timeout=30)
assert adb('shell','getprop','ro.serialno').decode().strip() == SERIAL
rows = [line.split() for line in adb('shell','ps','-A','-o','UID,PID,NAME').decode().splitlines()[1:]]
uid = next(row[0] for row in rows if row[2] == PACKAGE)
assert int(uid) >= 10000
pids = [row[1] for row in rows if row[0] == uid and row[2] == 'libproot.so']
assert pids, 'No app-owned PRoot running'
for pid in pids:
    environment = adb('exec-out','run-as',PACKAGE,'cat','/proc/'+pid+'/environ').split(b'\0')
    assert b'PROOT_NO_SECCOMP=1' in environment, 'PRoot compatibility setting missing in actual PID '+pid
apk = adb('shell','pm','path',PACKAGE).decode().strip().removeprefix('package:')
report = dict(serial=SERIAL, app_uid=int(uid), proot_pids=pids, proot_no_seccomp=True,
              apk_sha256=adb('shell','sha256sum',apk).decode().split()[0],
              scope='Actual launch configuration only; affected stock phone must retest')
(ROOT/'evidence/proot-compatibility.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))

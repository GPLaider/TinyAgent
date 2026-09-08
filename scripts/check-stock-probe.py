"""Read-only acceptance of the fixed probe launched by the Android app itself."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ADB = Path.home() / 'AppData/Local/Android/Sdk/platform-tools/adb.exe'
SERIAL = 'USB_TEST_SERIAL'
PACKAGE = 'io.github.gplaider.tinyagent.debug'


def adb(*args):
    return subprocess.check_output([str(ADB), '-s', SERIAL, *args], timeout=30).decode().strip()


assert adb('shell', 'getprop', 'ro.serialno') == SERIAL
assert adb('shell', 'id').startswith('uid=2000(')
assert adb('shell', 'getenforce') == 'Enforcing'
log = adb('shell', 'run-as', PACKAGE, 'cat', 'files/stock-probe.log')
uid = int(re.search(r'^host_uid=(\d+)', log).group(1))
assert uid >= 10000 and 'host_context=u:r:untrusted_app:' in log
assert 'Fedora release 44 (Forty Four)' in log
assert 'PASS: Fedora userspace ran under the ordinary Android app UID.' in log
assert 'FAIL:' not in log and log.count('exit=0') >= 2
apk = adb('shell', 'pm', 'path', PACKAGE).removeprefix('package:')
report = dict(serial=SERIAL, host_uid=uid, shell_uid=2000, selinux='Enforcing',
              boot_state=adb('shell', 'getprop', 'ro.boot.verifiedbootstate'),
              apk_sha256=adb('shell', 'sha256sum', apk).split()[0],
              log_sha256=hashlib.sha256(log.encode()).hexdigest(),
              passed=True, scope='App UID Fedora execution only; not clean-stock or release acceptance')
(ROOT / 'evidence/stock-probe-acceptance.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))

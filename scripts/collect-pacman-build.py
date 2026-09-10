"""Copy one phone build's evidence and verify a selected APK against its recorded hash."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('run')
parser.add_argument('--apk-name')
parser.add_argument('--installed-package')
args = parser.parse_args()
assert args.run.replace('-', '').isalnum()
root = Path(__file__).resolve().parents[1]
adb = str(Path.home()/'AppData/Local/Android/Sdk/platform-tools/adb.exe')
prefix = [adb, '-s', '000501423003390']
package = 'io.github.gplaider.tinyagent.debug'
def read(*argv):
    return subprocess.check_output(prefix+list(argv), timeout=120)
assert read('shell', 'getprop', 'ro.serialno').strip() == b'000501423003390'
dest = root/'evidence'/('pacman-'+args.run)
dest.mkdir(exist_ok=True)
base = 'files/linux/workspace/tinyagent-six-builds/'+args.run
for name in ['result.json', 'build.log', 'source.patch']:
    (dest/name).write_bytes(read('exec-out', 'run-as', package, 'cat', base+'/'+name))
result = json.loads((dest/'result.json').read_text())
if args.apk_name:
    assert result['status'] == 'passed' and result['exit_code'] == 0
    apk = next(a for a in result['apks'] if Path(a['path']).name == args.apk_name)
    assert apk['path'].startswith('/workspace/tinyagent-six-builds/') and '..' not in Path(apk['path']).parts
    target = root.parent/'artifacts'/('pacman-'+args.apk_name)
    target.write_bytes(read('exec-out', 'run-as', package, 'cat', 'files/linux/workspace/'+apk['path'].removeprefix('/workspace/')))
    assert target.stat().st_size == apk['size']
    assert hashlib.sha256(target.read_bytes()).hexdigest() == apk['sha256']
    result['collected_apk'] = str(target)
    if args.installed_package:
        assert all(c.isalnum() or c == '.' for c in args.installed_package)
        installed = read('shell', 'pm', 'path', args.installed_package).decode().strip().removeprefix('package:')
        assert installed.startswith('/data/app/') and '\n' not in installed
        checksum = read('shell', 'sha256sum', installed).decode().split()[0]
        assert checksum == apk['sha256']
        result['installed'] = dict(package=args.installed_package, sha256=checksum)
        assert b'UI hierchary dumped to:' in read('shell', 'uiautomator', 'dump', '/sdcard/tinyagent-build-acceptance.xml')
        (dest/'visible.png').write_bytes(read('exec-out', 'screencap', '-p'))
        (dest/'visible.xml').write_bytes(read('shell', 'cat', '/sdcard/tinyagent-build-acceptance.xml'))
    (dest/'collection.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(dict(evidence=str(dest), status=result['status'], seconds=result.get('seconds'), installed=result.get('installed'))))

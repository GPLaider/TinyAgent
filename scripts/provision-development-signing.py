"""Provision the existing development signer directly into one app-private phone directory.

Never transfers a release key or exposes private bytes in stdout/ADB shared storage.
The user explicitly requested host/phone signature consistency.
"""
import argparse
import base64
import hashlib
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--serial', choices=['100.79.65.42:5555', '100.79.134.53:5555', '000501423003390'], required=True)
args = parser.parse_args()
adb = Path.home() / 'AppData/Local/Android/Sdk/platform-tools/adb.exe'
package = 'io.github.gplaider.tinyagent.debug'
directory = 'files/linux/home/.tinyagent/signing'
expected = 'a3ef78ae0bfdfc30307e3448e138eca29adf39d966f89af116bbce151abc1ed2'

def run(*argv, data=None):
    return subprocess.run([str(adb), '-s', args.serial, *argv], input=data,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=30).stdout

hardware = {'100.79.65.42:5555': 'ZY22HZPLL8', '100.79.134.53:5555': 'ZY22J58799', '000501423003390': '000501423003390'}
assert run('shell', 'getprop', 'ro.serialno').decode().strip() == hardware[args.serial]
assert int(run('shell', 'run-as', package, 'id', '-u')) >= 10000
key = Path.home() / '.android/debug.keystore'
certificate = subprocess.run(['keytool', '-exportcert', '-keystore', str(key), '-alias', 'androiddebugkey',
                              '-storepass', 'android'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout
assert hashlib.sha256(certificate).hexdigest() == expected, 'Unexpected host development signer; nothing copied'
run('shell', 'run-as', package, 'mkdir', '-p', directory)
run('shell', 'run-as', package, 'chmod', '700', directory)
decoder = '/data/local/tmp/tinyagent-decode-private-file.sh'
run('push', str(Path(__file__).with_name('decode-private-file.sh')), decoder)

def private_file(name, data):
    target = directory + '/' + name
    # Existing identities/configuration are never silently replaced.
    names = run('shell', 'run-as', package, 'ls', directory).decode().splitlines()
    if name in names:
        digest = run('shell', 'run-as', package, 'sha256sum', target).decode().split()[0]
        assert digest == hashlib.sha256(data).hexdigest(), 'Existing private signing file differs'
        return
    temporary = target + '.part'
    encoded = target + '.encoded.part'
    payload = base64.b64encode(data) + b'\n'
    run('shell', 'run-as', package, 'touch', encoded)
    run('shell', 'run-as', package, 'chmod', '600', encoded)
    # Binary stdin was truncated by this Windows ADB transport. Transfer ASCII
    # only, still entirely into app-private storage, and decode on the device.
    with subprocess.Popen([str(adb), '-s', args.serial, 'shell', '-T', 'run-as', package,
                           'dd', 'of=' + encoded, 'bs=1', 'count=' + str(len(payload))],
                          stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) as process:
        process.stdin.write(payload)
        process.stdin.flush()
        try: assert process.wait(timeout=30) == 0, 'Private transfer failed'
        except subprocess.TimeoutExpired:
            process.kill()
            raise
    run('shell', 'run-as', package, '/system/bin/sh', decoder, encoded, temporary)
    digest = run('shell', 'run-as', package, 'sha256sum', temporary).decode().split()[0]
    assert digest == hashlib.sha256(data).hexdigest(), 'Private transfer integrity failure'
    run('shell', 'run-as', package, 'mv', temporary, target)
    run('shell', 'run-as', package, 'rm', encoded)

private_file('development.keystore', key.read_bytes())
private_file('development.properties', b'storeFile=/root/.tinyagent/signing/development.keystore\nstorePassword=android\nkeyAlias=androiddebugkey\nkeyPassword=android\n')
print('App-private development signer provisioned; certificate SHA256=' + expected)

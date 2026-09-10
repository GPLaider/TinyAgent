"""Create an owner-only release signer outside source control; print public fingerprint only."""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('directory', type=Path)
args = parser.parse_args()
directory = args.directory.resolve()
assert not directory.exists(), 'Signer directory already exists; reuse it, never overwrite keys'
assert not any((p / '.git').exists() for p in (directory, *directory.parents)), 'Keep signing material outside repositories'
keytool = shutil.which('keytool')
assert keytool, 'JDK keytool required'
directory.mkdir(mode=0o700)
if os.name == 'nt':
    identity = subprocess.check_output(['whoami', '/user', '/fo', 'csv', '/nh'], text=True)
    sid = next(csv.reader(io.StringIO(identity.strip())))[1]
    assert sid.startswith('S-1-5-')
    subprocess.run(['icacls', str(directory), '/inheritance:r', '/grant:r', '*' + sid + ':(OI)(CI)F'],
                   check=True, stdout=subprocess.DEVNULL)
password = secrets.token_hex(32)
env = dict(os.environ, TINYAGENT_SIGNER_PASSWORD=password)
store = directory / 'release.p12'
result = subprocess.run([keytool, '-genkeypair', '-keystore', str(store), '-storetype', 'PKCS12',
    '-alias', 'tinyagent-release', '-keyalg', 'RSA', '-keysize', '4096', '-validity', '10000',
    '-dname', 'CN=TinyAgent Release, O=TinyAgent', '-storepass:env', 'TINYAGENT_SIGNER_PASSWORD',
    '-keypass:env', 'TINYAGENT_SIGNER_PASSWORD', '-noprompt'], env=env, capture_output=True)
assert result.returncode == 0, 'Key generation failed; private directory retained for inspection'
certificate = subprocess.check_output([keytool, '-exportcert', '-keystore', str(store),
    '-alias', 'tinyagent-release', '-storepass:env', 'TINYAGENT_SIGNER_PASSWORD'], env=env)
fingerprint = hashlib.sha256(certificate).hexdigest()
assert fingerprint not in {'a3ef78ae0bfdfc30307e3448e138eca29adf39d966f89af116bbce151abc1ed2',
                          'a40da80a59d170caa950cf15c18c454d47a39b26989d8b640ecd745ba71bf5dc'}
properties = directory / 'release.properties'
with properties.open('x', encoding='utf-8') as stream:
    stream.write(f'storeFile={store.as_posix()}\nstorePassword={password}\nkeyAlias=tinyagent-release\nkeyPassword={password}\n')
if os.name != 'nt':
    store.chmod(0o600)
    properties.chmod(0o600)
(directory / 'certificate.der').write_bytes(certificate)
metadata = {'certificate_sha256': fingerprint, 'alias': 'tinyagent-release', 'algorithm': 'RSA-4096',
            'package': 'io.github.gplaider.tinyagent', 'scope': 'Production signer; private key remains outside source control'}
(directory / 'public-metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
print(json.dumps(metadata))

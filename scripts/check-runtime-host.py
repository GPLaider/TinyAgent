"""Offline checks, never evidence of Android installation or foreground behavior."""
import hashlib
import os
from pathlib import Path
import subprocess
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BASH = 'C:/Program Files/Git/bin/bash.exe'
CACHE = Path('C:/Users/Administrator/.gradle/caches/modules-2/files-2.1')


def run(argv, **kwargs):
    result = subprocess.run(argv, cwd=kwargs.pop('cwd', ROOT), capture_output=True, text=True,
                            encoding='utf-8', errors='replace', timeout=90, **kwargs)
    if result.returncode or 'An exception has occurred in the compiler' in result.stderr:
        raise RuntimeError(result.stdout + result.stderr)
    return result


def main():
    prepare = ROOT / 'preroot/prepare.sh'
    source = prepare.read_text(encoding='utf-8')
    assets = ROOT / 'app/src/main/assets'
    pins = {
        'fedora-44-arm64-rootfs.tar.gz': '3a3661a77d5fdb1e4bd10be484142683630c1ffb4c371931d46a42459fd4c125',
        'opencode-linux-arm64.tar.gz': 'b877f7baa8d60611b9a638209c84868e5dea9139c8dec622943d25f29c07f205',
    }
    for name, digest in pins.items():
        with (assets / (name + '.bin')).open('rb') as stream:
            assert hashlib.file_digest(stream, 'sha256').hexdigest() == digest, name
        stock = (ROOT / 'app/src/main/java/io/github/gplaider/tinyagent/LocalLinuxRuntime.java').read_text(encoding='utf-8')
        assert digest in stock
    print('Bundled archive SHA256: 2 passed', flush=True)
    for script in (ROOT / 'preroot').glob('*.sh'):
        run([BASH, '-n', str(script)])
    print('PreRoot shell syntax: passed', flush=True)
    for uid, abi, args, expected in [
        ('2000', 'arm64-v8a', [], 'root ADB is required'),
        ('0', 'x86_64', [], 'arm64 Android is required'),
        ('0', 'arm64-v8a', [], 'usage:'),
        ('0', 'arm64-v8a', ['relative', 'relative'], 'archive must be in Android /data'),
    ]:
        result = subprocess.run([BASH, 'scripts/preroot-guard-check.sh',
                                 'preroot/prepare.sh', *args], cwd=ROOT,
                                env={**os.environ, 'TEST_UID': uid, 'TEST_ABI': abi},
                                capture_output=True, text=True, timeout=10)
        assert result.returncode == 1 and expected in result.stderr, result
    print('Installation preconditions: 4 host-only checks passed', flush=True)
    jars = [Path('C:/Users/Administrator/AppData/Local/Android/Sdk/platforms/android-36/android.jar')]
    for directory, name in [('dev.mobile/dadb/1.2.10', 'dadb-1.2.10.jar'),
                            ('com.squareup.okio/okio/2.10.0', 'okio-jvm-2.10.0.jar'),
                            ('org.jetbrains.kotlin/kotlin-stdlib/2.3.21', 'kotlin-stdlib-2.3.21.jar')]:
        matches = list((CACHE / directory).rglob(name))
        assert len(matches) == 1
        jars.append(matches[0])
    build = Path(tempfile.mkdtemp(prefix='tinyagent-compile-'))
    classpath = []
    for jar in jars:
        shutil.copyfile(jar, build / jar.name)
        classpath.append(jar.name)
    classes = build / 'classes'
    classes.mkdir(parents=True, exist_ok=True)
    java = sorted((ROOT / 'app/src/main/java').rglob('*.java'))
    for path in java:
        shutil.copyfile(path, build / path.name)
    run(['javac', '-encoding', 'UTF-8', '-classpath', os.pathsep.join(classpath),
         '-d', 'classes', *[path.name for path in java]], cwd=build)
    print(f'Android SDK 36 compilation: {len(java)} Java sources passed', flush=True)


if __name__ == '__main__':
    main()

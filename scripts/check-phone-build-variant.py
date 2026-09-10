"""Execute the real shell wrapper with fake compiler tools; verify signing guard and Gradle task selection."""
import os
from pathlib import Path
import shutil
import shlex
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
bash = shutil.which('bash') if os.name != 'nt' else 'C:/Program Files/Git/bin/bash.exe'
assert bash and Path(bash).is_file()

def shell_path(path):
    value = Path(path).resolve().as_posix()
    return '/' + value[0].lower() + value[2:] if os.name == 'nt' else value

with tempfile.TemporaryDirectory(prefix='tinyagent-build-check-') as name:
    fixture = Path(name)
    (fixture / 'scripts').mkdir()
    (fixture / 'bin').mkdir()
    wrapper = fixture / 'scripts/build-android-fedora.sh'
    shutil.copyfile(root / 'scripts/build-android-fedora.sh', wrapper)
    for filename, contents in {
        'bin/uname': '#!/bin/sh\nprintf "aarch64\\n"\n',
        'bin/git': '#!/bin/sh\nexit 0\n',
        'gradlew': '#!/bin/sh\nprintf "GRADLE_ARG=%s\\n" "$@"\n',
    }.items():
        path = fixture / filename
        path.write_text(contents, newline='\n')
        path.chmod(0o755)
    env = {k: v for k, v in os.environ.items() if not k.startswith('TINYAGENT_')}
    env.update(TINYAGENT_EXECUTION_PROVIDER='fedora-preroot',
               PATH=shell_path(fixture / 'bin') + ':/usr/bin:/bin', JAVA_HOME='/unused-test-jdk')
    setup = fixture / 'test-env.sh'
    setup.write_text('export PATH=' + shlex.quote(env['PATH']) + '\n', newline='\n')
    env['BASH_ENV'] = shell_path(setup)
    def run(**changes):
        return subprocess.run([bash, str(wrapper)], env=dict(env, **changes), capture_output=True, text=True)
    debug = run()
    assert debug.returncode == 0 and 'GRADLE_ARG=:app:assembleDebug' in debug.stdout, (debug.returncode, debug.stdout, debug.stderr)
    missing = run(TINYAGENT_BUILD_TYPE='release')
    assert missing.returncode != 0 and 'Release signing properties are required' in missing.stderr
    assert 'GRADLE_ARG=' not in missing.stdout
    props = fixture / 'fake-signing.properties'
    props.write_text('# Test placeholder; no signing key\n')
    release = run(TINYAGENT_BUILD_TYPE='release', TINYAGENT_RELEASE_SIGNING_PROPERTIES=shell_path(props))
    assert release.returncode == 0 and 'GRADLE_ARG=:app:assembleRelease' in release.stdout, release.stderr
    invalid = run(TINYAGENT_BUILD_TYPE='invalid')
    assert invalid.returncode != 0 and 'GRADLE_ARG=' not in invalid.stdout
    print('PASS: debug default, release signing guard, release task, invalid variant rejection; no real compiler invoked')

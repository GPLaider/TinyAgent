"""Run inside phone Fedora; a held slot must not leave a waiting build process."""
import fcntl
import os
from pathlib import Path
import subprocess
import sys
import tempfile

assert os.environ.get('TINYAGENT_EXECUTION_PROVIDER') == 'fedora-local'
script = Path(sys.argv[1])
assert script.is_file()
base = Path('/workspace/tinyagent-six-builds')
before = set(base.glob('*-build-*'))
with (base/'.build.lock').open('a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    child = subprocess.Popen([sys.executable, str(script), 'vlc-android'],
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        output, _ = child.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        child.kill()
        child.communicate()
        raise AssertionError('Busy build remained alive instead of declining admission')
    assert child.returncode == 75, (child.returncode, output)
    assert 'BUILD_NOT_STARTED: phone build slot busy' in output, output
assert set(base.glob('*-build-*')) == before, 'Declined build created a result directory'

# GNU make passes the command-line override to recursive makes, covering VLC's Meson variable.
with tempfile.TemporaryDirectory() as directory:
    makefile = Path(directory)/'Makefile'
    makefile.write_text('MESONCOMPILEFLAGS =\nall:\n\t@$(MAKE) --no-print-directory -f '+str(makefile)+' child\nchild:\n\t@echo $(MESONCOMPILEFLAGS)\n')
    result = subprocess.check_output(['make', '--no-print-directory', '-f', str(makefile)],
                                    env=dict(os.environ, MAKEFLAGS='-j1 MESONCOMPILEFLAGS=-j1'), text=True)
    assert result.strip() == '-j1', result
print('PASS: busy admission exits 75, no waiting child/results; recursive Make retains Meson -j1')

"""Finish the failed first checkout without resetting or bypassing VLC patch checks."""
import os
from pathlib import Path
import subprocess

base = Path('/workspace/tinyagent-six-builds/vlc-android/libvlcjni')
source = base/'vlc'
assert os.environ.get('TINYAGENT_EXECUTION_PROVIDER') == 'fedora-local'
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source).strip() == b'ac6c2a405d652b5576128ceb9fec2c342f0e83ec'
assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=source).strip()
assert not (source/'.git/rebase-apply').exists(), 'Inspect interrupted git am before recovery'
env = dict(os.environ, GIT_COMMITTER_NAME='TinyAgent build', GIT_COMMITTER_EMAIL='build@localhost')
patches = sorted((base/'libvlc/patches').glob('*.patch'))
assert patches
subprocess.run(['git', 'am', '--message-id', *map(str, patches)], cwd=source, env=env, check=True)
print('VLC pinned custom patches applied; normal build checks remain enabled')

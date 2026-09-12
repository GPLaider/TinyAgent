"""Export and verify the GUI delta against the pinned upstream without changing its index."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
upstream = root.parent / 'upstream/opencode'
scopes = ['packages/app', 'packages/session-ui', 'packages/ui']
pin = '16747470f976aca3d362ad730bcd3fe82ecc2c9a'

def git(*args, env=None):
    result = subprocess.run(['git', '-C', str(upstream), *args], env=env, capture_output=True)
    if result.returncode:
        raise RuntimeError('GUI patch verification failed: ' + result.stderr.decode(errors='replace'))
    return result.stdout

assert git('rev-parse', 'HEAD').decode().strip() == pin
generated = {
    'packages/session-ui/src/components/message-file.d.ts',
    'packages/session-ui/src/v2/components/attachment-card-v2.d.ts',
    'packages/session-ui/src/v2/components/comment-card-v2.d.ts',
    'packages/session-ui/src/v2/components/prompt-input/index.d.ts',
    'packages/session-ui/src/v2/components/prompt-input/interaction.d.ts',
    'packages/session-ui/src/v2/components/prompt-input/types.d.ts',
}
untracked = set(git('ls-files', '--others', '--exclude-standard', '--', *scopes).decode().splitlines())
added = {
    'packages/app/src/pages/session/timeline/timeline-row.test.ts',
    'packages/session-ui/src/components/session-turn-status.ts',
    'packages/session-ui/src/components/session-turn-status.test.ts',
}
# Reviewed compiler declarations have tracked TS/TSX sources; they are not runtime inputs.
assert untracked <= generated | added, 'Untracked GUI files need explicit review before export'
for name in untracked & generated:
    stem = name.removesuffix('.d.ts')
    assert git('ls-files', '--', stem + '.ts', stem + '.tsx'), name
with tempfile.TemporaryDirectory(prefix='tinyagent-gui-patch-') as directory:
    temporary = Path(directory)
    candidate = temporary / 'gui.patch'
    env = dict(os.environ, GIT_INDEX_FILE=str(temporary / 'index'))
    git('read-tree', pin, env=env)
    git('add', '-u', '--', *scopes, env=env)
    git('add', '--', *sorted(added), env=env)
    patch = git('diff', '--cached', '--binary', pin, '--', *scopes, env=env)
    assert patch
    candidate.write_bytes(patch)
    git('read-tree', pin, env=env)
    git('apply', '--cached', '--check', str(candidate), env=env)
    git('apply', '--cached', str(candidate), env=env)
    # The patched pinned tree must describe every tracked current GUI source change.
    git('diff', '--exit-code', '--', *scopes, env=env)
    target = root / 'patches/opencode-mobile-ux.patch'
    target.write_bytes(patch)
print(json.dumps({'upstream': pin, 'patch_sha256': hashlib.sha256(patch).hexdigest(),
                  'bytes': len(patch), 'scopes': scopes, 'excluded_generated_declarations': sorted(untracked & generated),
                  'base_apply_and_working_tree_match': True}))

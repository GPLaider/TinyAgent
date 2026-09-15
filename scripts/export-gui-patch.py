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
    'packages/app/e2e/regression/mobile-session-actions.spec.ts',
    'packages/app/e2e/regression/mobile-settings.spec.ts',
    'packages/app/e2e/regression/prompt-long-model-mobile.spec.ts',
    'packages/app/e2e/regression/session-access.spec.ts',
    'packages/app/e2e/regression/session-reconnect.spec.ts',
    'packages/app/e2e/regression/session-work-status.spec.ts',
    'packages/app/src/components/settings-v2/mobile.css',
    'packages/app/src/pages/home/home-list-actions.tsx',
    'packages/app/src/pages/session/composer/tinyagent-access.test.ts',
    'packages/app/src/pages/session/composer/tinyagent-access.tsx',
    'packages/app/src/pages/session/composer/session-work-status.tsx',
    'packages/app/src/pages/session/timeline/timeline-row.test.ts',
    'packages/session-ui/src/components/session-turn-status.ts',
    'packages/session-ui/src/components/session-turn-status.test.ts',
}
# Reviewed compiler declarations have tracked TS/TSX sources; they are not runtime inputs.
assert untracked <= generated | added, 'Untracked GUI files need explicit review before export'
base_files = set(git('ls-tree', '-r', '--name-only', pin, '--', *scopes).decode().splitlines())
indexed_files = set(git('ls-files', '--', *scopes).decode().splitlines())
indexed_added = indexed_files - base_files
assert indexed_added <= added, 'Indexed GUI additions need explicit review before export: ' + repr(sorted(indexed_added - added))
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
    current_tree = git('write-tree', env=env).decode().strip()
    patch = git('diff', '--cached', '--binary', pin, '--', *scopes, env=env)
    assert patch
    candidate.write_bytes(patch)
    git('read-tree', pin, env=env)
    git('apply', '--cached', '--check', str(candidate), env=env)
    git('apply', '--cached', str(candidate), env=env)
    assert git('write-tree', env=env).decode().strip() == current_tree
    target = root / 'patches/opencode-mobile-ux.patch'
    target.write_bytes(patch)
print(json.dumps({'upstream': pin, 'patch_sha256': hashlib.sha256(patch).hexdigest(),
                  'bytes': len(patch), 'scopes': scopes, 'excluded_generated_declarations': sorted(untracked & generated),
                  'base_apply_and_working_tree_match': True}))

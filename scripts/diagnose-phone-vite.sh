#!/usr/bin/bash
set -eu
cd /workspace/opencode-v1.18.29/packages/app
export PATH=/opt/tinyagent-build/bun-linux-aarch64:$PATH
python3 - <<'PY'
import json, pathlib
for name in ['vite', '@sentry/vite-plugin', '@tailwindcss/vite', 'vite-plugin-solid']:
    root = pathlib.Path('node_modules') / name
    metadata = json.loads((root / 'package.json').read_text())
    print(name, 'resolved=', root.resolve(), 'main=', metadata.get('main'), 'exports=', metadata.get('exports'))
    for path in root.glob('dist/*'):
        print(path, 'file=', path.is_file(), 'resolved=', path.resolve())
PY
cat > /workspace/opencode-v1.18.29/packages/app/tinyagent-vite-diagnostic.mjs <<'JS'
try {
  const { build } = await import('vite');
  await build();
} catch (error) {
  console.error(error);
  console.error(error?.stack, error?.cause?.stack);
  process.exitCode = 1;
}
JS
node ./tinyagent-vite-diagnostic.mjs

"""Package the locally built, pinned OpenCode GUI without changing the backend."""
import base64
import hashlib
import json
import mimetypes
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = Path(sys.argv[1]).resolve()
PIN = '16747470f976aca3d362ad730bcd3fe82ecc2c9a'
assert subprocess.check_output(['git', '-C', str(UPSTREAM), 'rev-parse', 'HEAD']).decode().strip() == PIN
dist = UPSTREAM / 'packages/app/dist'
assets = ROOT / 'app/src/main/assets'
target = assets / 'web-ui'
target.mkdir(exist_ok=True)
files = {}
hashes = {}
types = {'.js': 'text/javascript', '.css': 'text/css', '.html': 'text/html', '.svg': 'image/svg+xml',
         '.wasm': 'application/wasm', '.woff2': 'font/woff2', '.ttf': 'font/ttf'}
for source in dist.rglob('*'):
    if not source.is_file() or source.suffix == '.map' or source.name == '_headers':
        continue
    relative = source.relative_to(dist)
    # Vite may copy a Windows symlink itself. Resolve known public assets explicitly.
    public = UPSTREAM / 'packages/app/public' / relative
    actual = public.resolve() if public.is_file() else source
    output = target / relative
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(actual, output)
    key = '/' + relative.as_posix()
    files[key] = types.get(source.suffix) or mimetypes.guess_type(source.name)[0] or 'application/octet-stream'
    hashes[key] = hashlib.sha256(output.read_bytes()).hexdigest()
assert not target.is_symlink() and target.resolve().is_relative_to(ROOT)
for stale in target.rglob('*'):
    if stale.is_file() and '/' + stale.relative_to(target).as_posix() not in files:
        assert stale.resolve().is_relative_to(target.resolve())
        stale.unlink()
html = (target / 'index.html').read_text(encoding='utf-8')
inline = re.findall(r'<script\b[^>]*>([\s\S]*?)</script>', html)
script_hashes = ' '.join("'sha256-" + base64.b64encode(hashlib.sha256(s.encode()).digest()).decode() + "'" for s in inline if s)
csp = ("default-src 'self'; script-src 'self' 'wasm-unsafe-eval' " + script_hashes
       + "; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:;"
         " connect-src 'self' data: blob:; worker-src 'self' blob:; object-src 'none'; base-uri 'self'")
manifest = dict(upstream=PIN, version='1.18.29', files=files, sha256=hashes, csp=csp)
(assets / 'web-ui-manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
print(f'Packaged GUI: {len(files)} files, {sum(p.stat().st_size for p in target.rglob("*") if p.is_file())} bytes')

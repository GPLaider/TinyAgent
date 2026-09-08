"""Install the upstream-pinned Bun to task-local storage, verifying release digest."""
import hashlib
import urllib.request
import zipfile
from pathlib import Path

root = Path('D:/TinyAgent-work/tools')
root.mkdir(exist_ok=True)
archive = root / 'bun-windows-x64-1.3.14.zip'
expected = '0a0620930b6675d7ba440e81f4e0e00d3cfbe096c4b140d3fff02205e9e18922'
if not archive.exists():
    part = archive.with_suffix('.part')
    urllib.request.urlretrieve('https://github.com/oven-sh/bun/releases/download/bun-v1.3.14/bun-windows-x64.zip', part)
    assert hashlib.file_digest(part.open('rb'), 'sha256').hexdigest() == expected
    part.replace(archive)
assert hashlib.file_digest(archive.open('rb'), 'sha256').hexdigest() == expected
with zipfile.ZipFile(archive) as package:
    (root / 'bun.exe').write_bytes(package.read('bun-windows-x64/bun.exe'))
print(root / 'bun.exe')

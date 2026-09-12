"""Validate every pinned overlay member before copying it into APK assets."""
import argparse,hashlib,io,json,tarfile,zipfile
from pathlib import Path,PurePosixPath
root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--installed-apk',type=Path)
args=parser.parse_args()
if args.installed_apk:
    with zipfile.ZipFile(args.installed_apk) as installed:
        names=('assets/dnfast-manifest.json','assets/dnfast-root-overlay.tar.gz.bin')
        for name,limit in zip(names,(1024*1024,64*1024*1024)):
            if installed.getinfo(name).file_size>limit:raise ValueError('Oversized dnfast input: '+name)
        manifest,archive=(installed.read(name) for name in names)
else:
    manifest=(root/'runtime/dnfast-1449710-manifest.json').read_bytes()
    archive=(root/'runtime/dnfast-1449710-root-overlay.tar.gz').read_bytes()
if hashlib.sha256(manifest).hexdigest()!='ec8599eb4b44266abbbcafa0952a67d29d96d4ff5572566ad403c0c425492699':
    raise ValueError('dnfast manifest hash mismatch')
data=json.loads(manifest)
if hashlib.sha256(archive).hexdigest()!=data['overlay_sha256']:raise ValueError('dnfast overlay hash mismatch')
with tarfile.open(fileobj=io.BytesIO(archive)) as source:
    found=set()
    for member in source:
        path=PurePosixPath(member.name)
        assert not path.is_absolute() and '..' not in path.parts,member.name
        if member.isdir():continue
        assert member.isfile() and member.name in data['files'],member.name
        assert member.name not in found,member.name
        assert hashlib.sha256(source.extractfile(member).read()).hexdigest()==data['files'][member.name],member.name
        found.add(member.name)
    assert found==set(data['files'])
assets=root/'app/src/main/assets'
assets.mkdir(parents=True,exist_ok=True)
for name,payload in (('dnfast-root-overlay.tar.gz.bin',archive),('dnfast-manifest.json',manifest)):
    partial=assets/(name+'.part')
    partial.write_bytes(payload)
    partial.replace(assets/name)
print(f'PASS: {len(found)} pinned dnfast files; exact overlay and manifest staged')

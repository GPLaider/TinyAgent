import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

root=Path('/work/output')
report={}
for name, binaries, libpath in [
    ('dnfast',[root/'dnfast',root/'dnfast-executor'],None),
    ('microdnf',[root/'micro-root/usr/bin/microdnf'],str(root/'micro-root/usr/lib64'))]:
    destination=root/'bundle'/name
    env=os.environ.copy()
    if libpath: env['LD_LIBRARY_PATH']=libpath
    libraries=set()
    for binary in binaries:
        assert binary.is_file(), binary
        shutil.copy2(binary,destination/'bin'/binary.name)
        output=subprocess.check_output(['ldd',str(binary)],env=env,text=True)
        assert 'not found' not in output,output
        libraries.update(re.findall(r'(?:=>\s+|^\s*)(/[^\s]+)',output,re.M))
    for library in libraries:
        p=Path(library)
        shutil.copy2(p,destination/'lib'/p.name,follow_symlinks=True)
    report[name]={str(p.relative_to(destination)):hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.rglob('*') if p.is_file()}
(root/'bundle/manifest.json').write_text(json.dumps(report,indent=2))

import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

root=Path('/workspace/tinyagent-package-bench-20260909')
archive=root/'tools.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='0f18cb8df898e1df8110bbfaf01ff00c433466e6dab6dd96bd4cc018262a855e'
target=root/'tools'
target.mkdir(exist_ok=True)
with tarfile.open(archive) as source: source.extractall(target,filter='data')
manifest=json.loads((target/'manifest.json').read_text())
for tool,files in manifest.items():
    for relative,expected in files.items():
        p=target/tool/relative
        assert p.resolve().is_relative_to(target.resolve())
        assert hashlib.sha256(p.read_bytes()).hexdigest()==expected,str(p)
results=[]
for tool,args in [('microdnf',['--version']),('dnfast',['--version']),('dnfast',['doctor'])]:
    directory=target/tool
    command=[str(directory/'lib/ld-linux-aarch64.so.1'),'--library-path',str(directory/'lib'),str(directory/'bin'/tool),*args]
    result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=90)
    results.append({'tool':tool,'args':args,'exit':result.returncode,'output':result.stdout})
(root/'compatibility.json').write_text(json.dumps(results,indent=2))
print(json.dumps(results))

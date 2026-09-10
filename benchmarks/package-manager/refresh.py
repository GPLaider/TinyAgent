"""First compatibility pass. Fresh tool caches; official Fedora release repo only."""
import json,os,signal,subprocess,time,sys
from pathlib import Path
root=Path('/workspace/tinyagent-package-bench-20260909')
if '--background' in sys.argv:
    with (root/'refresh-worker.log').open('w') as out:
        child=subprocess.Popen([sys.executable,str(Path(__file__).resolve())],stdin=subprocess.DEVNULL,stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
    (root/'refresh-worker.pid').write_text(str(child.pid)); print('refresh_worker_pid='+str(child.pid));sys.exit(0)
report=[]
for name in ['dnfast','microdnf','dnf5']:
    p=root/'tools'/name
    command=([str(p/'lib/ld-linux-aarch64.so.1'),'--library-path',str(p/'lib'),str(p/'bin'/name)] if name!='dnf5' else ['/usr/bin/dnf5'])
    cache=root/'cache-first'/name
    if name=='dnfast': args=['repo','makecache','--repo','fedora']
    elif name=='microdnf': args=['--setopt=cachedir='+str(cache),'--disablerepo=*','--enablerepo=fedora','makecache']
    else: args=['--setopt=cachedir='+str(cache),'--disable-repo=*','--enable-repo=fedora','makecache']
    start=time.monotonic()
    log=root/(name+'-refresh-first.log')
    with log.open('w') as out:
        process=subprocess.Popen(command+args,stdout=out,stderr=subprocess.STDOUT,start_new_session=True,env={**os.environ,'LC_ALL':'C'})
        timeout=False
        try: process.wait(timeout=180)
        except subprocess.TimeoutExpired:
            timeout=True;os.killpg(process.pid,signal.SIGTERM)
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
    row={'tool':name,'seconds':time.monotonic()-start,'exit':process.returncode,'timeout':timeout,'tail':log.read_text(errors='replace')[-3500:]}
    report.append(row)
    (root/'refresh-first.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(row),flush=True)

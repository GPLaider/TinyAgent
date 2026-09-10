"""Matched read-only CLI workload; separate from repository refresh/install tests."""
import hashlib,json,os,statistics,subprocess,tempfile,time
from pathlib import Path
root=Path('/workspace/tinyagent-package-bench-20260909')
tools={}
for name in ['microdnf','dnfast']:
    p=root/'tools'/name
    tools[name]=[str(p/'lib/ld-linux-aarch64.so.1'),'--library-path',str(p/'lib'),str(p/'bin'/name)]
tools['dnf5']=['/usr/bin/dnf5']
commands={'help':{name:['--help'] for name in tools},'repo-list':{'microdnf':['repolist'],'dnf5':['repo','list'],'dnfast':['repo','list']}}
report={'scope':'read-only help and configured repository listing; no download/install claims',
        'identity':Path('/proc/self/status').read_text(),'tools':tools,'trials':[]}
for workload,mapping in commands.items():
    names=['microdnf','dnf5','dnfast']
    for trial in range(7):
        order=names[trial%3:]+names[:trial%3]
        if trial%2: order=order[::-1]
        for name in order:
            with tempfile.TemporaryFile() as output:
                start=time.monotonic_ns()
                process=subprocess.Popen(tools[name]+mapping[name],stdout=output,stderr=subprocess.STDOUT,env={**os.environ,'LC_ALL':'C'})
                _,status,usage=os.wait4(process.pid,0)
                process.returncode=os.waitstatus_to_exitcode(status)
                elapsed=(time.monotonic_ns()-start)/1e9
                output.seek(0);text=output.read().decode(errors='replace')
            report['trials'].append({'workload':workload,'trial':trial,'tool':name,'seconds':elapsed,'exit':process.returncode,'maxrssKiB':usage.ru_maxrss,'output':text})
summary=[]
for workload in commands:
    for name in tools:
        runs=[t for t in report['trials'] if t['workload']==workload and t['tool']==name and t['trial']>0]
        summary.append({'workload':workload,'tool':name,'medianSeconds':statistics.median(t['seconds'] for t in runs),'medianRssKiB':statistics.median(t['maxrssKiB'] for t in runs),'exits':sorted(set(t['exit'] for t in runs))})
report['summary']=summary
(root/'compare.json').write_text(json.dumps(report,indent=2))
print(json.dumps(summary))

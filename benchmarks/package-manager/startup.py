"""Measure process startup only. Never label this as install/download throughput."""
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import tempfile
import time

root=Path('/workspace/tinyagent-package-bench-20260909')
root.mkdir(exist_ok=True)
tools=['/usr/bin/microdnf','/usr/bin/dnf5']
report={'scope':'CLI --version process startup; existing OS page cache; no RPM transaction',
        'identity':Path('/proc/self/status').read_text(), 'tools':{}, 'trials':[]}
for tool in tools:
    p=Path(tool)
    report['tools'][tool]={'realpath':str(p.resolve()),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
for trial in range(8):
    for tool in (tools if trial%2==0 else tools[::-1]):
        with tempfile.TemporaryFile() as output:
            start=time.monotonic_ns()
            process=subprocess.Popen([tool,'--version'],stdout=output,stderr=subprocess.STDOUT)
            _,status,usage=os.wait4(process.pid,0)
            process.returncode=os.waitstatus_to_exitcode(status)
            elapsed=(time.monotonic_ns()-start)/1e9
            output.seek(0)
            text=output.read().decode(errors='replace')
        report['trials'].append({'trial':trial,'tool':tool,'seconds':elapsed,'exit':process.returncode,
                                 'maxrssKiB':usage.ru_maxrss,'output':text})
        assert process.returncode==0,text
report['summary']={tool:{'medianSeconds':statistics.median(t['seconds'] for t in report['trials'] if t['tool']==tool and t['trial']>0)} for tool in tools}
target=root/'startup.json'
target.write_text(json.dumps(report,indent=2))
print(json.dumps({'tools':report['tools'],'summary':report['summary'],'scope':report['scope'],'report':str(target)}))

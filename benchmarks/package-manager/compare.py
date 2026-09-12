"""Matched read-only CLI workload; separate from repository refresh/install tests."""
import json,os,statistics,subprocess,tempfile,time
from pathlib import Path


def summarize(trials, workloads, tools, expected_runs=6):
    """Publish medians only for complete, successful measured cells.

    Trial zero is warmup, retained in raw data and warmupExits. A partially
    successful cell cannot advertise the speed of only its surviving runs.
    This exit-status gate does not establish semantic package-manager parity.
    """
    summary=[]
    for workload in workloads:
        for name in tools:
            cell=[t for t in trials if t['workload']==workload and t['tool']==name]
            runs=[t for t in cell if t['trial']>0]
            failed=sum(t['exit']!=0 for t in runs)
            complete=(len(runs)==expected_runs and
                      {t['trial'] for t in runs}==set(range(1,expected_runs+1)))
            status='failed' if failed else 'passed' if complete else 'incomplete'
            summary.append({
                'workload':workload,'tool':name,'status':status,
                'medianSeconds':statistics.median(t['seconds'] for t in runs) if status=='passed' else None,
                'medianRssKiB':statistics.median(t['maxrssKiB'] for t in runs) if status=='passed' else None,
                'successfulRuns':len(runs)-failed,'failedRuns':failed,'expectedRuns':expected_runs,
                'exits':sorted({t['exit'] for t in runs}),
                'warmupExits':sorted({t['exit'] for t in cell if t['trial']==0}),
            })
    return summary


def main():
    root=Path('/workspace/tinyagent-package-bench-20260909')
    tools={}
    for name in ['microdnf','dnfast']:
        p=root/'tools'/name
        tools[name]=[str(p/'lib/ld-linux-aarch64.so.1'),'--library-path',str(p/'lib'),str(p/'bin'/name)]
    tools['dnf5']=['/usr/bin/dnf5']
    commands={'help':{name:['--help'] for name in tools},'repo-list':{'microdnf':['repolist'],'dnf5':['repo','list'],'dnfast':['repo','list']}}
    report={'scope':'read-only help and configured repository listing; no download/install claims',
            'summaryPolicy':'Trial 0 is warmup; medians require all six measured trials to exit 0. Failed or incomplete cells have null medians. Exit 0 alone does not establish semantic parity.',
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
    report['summary']=summarize(report['trials'],commands,tools)
    (root/'compare.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report['summary']))


if __name__=='__main__':
    main()

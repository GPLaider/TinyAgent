"""Pacman fresh preparation observer. Existing rootfs is preserved separately."""
import subprocess, time, json, re
from pathlib import Path
import xml.etree.ElementTree as ET
adb=str(Path.home()/'AppData/Local/Android/Sdk/platform-tools/adb.exe')
package='io.github.gplaider.tinyagent.debug'
def run(*args): return subprocess.check_output([adb,'-s','000501423003390',*args],timeout=30).decode()
assert run('shell','getprop','ro.serialno').strip()=='000501423003390'
run('shell','input','keyevent','KEYCODE_HOME')
run('shell','input','keyevent','KEYCODE_SLEEP')
samples=[]
last=None
try:
    for _ in range(600):
        root=ET.fromstring(run('shell','run-as',package,'cat','shared_prefs/runtime.xml'))
        prefs={n.get('name'): n.get('value') if n.get('value') is not None else n.text for n in root}
        state=(prefs.get('status'),prefs.get('percent'))
        power=run('shell','dumpsys','power')
        # Power dumps include historical ACQ/REL entries. Inspect active locks only.
        active_locks=re.search(r'Wake Locks: size=.*?(?=\n\s*\n)', power, re.S)
        held=active_locks is not None and 'TinyAgent:EnvironmentPreparation' in active_locks.group(0)
        if state!=last:
            sample=dict(status=state[0],percent=int(state[1] or -1),screen_off='mWakefulness=Asleep' in power or 'mWakefulness=Dozing' in power,
                        wakelock=held)
            samples.append(sample)
            print(json.dumps(sample,ensure_ascii=False),flush=True)
            last=state
        if state[0].startswith('Fedora 설치 완료'):
            assert not held, 'Preparation lock leaked after readiness'
            break
        assert not state[0].startswith('환경 준비 실패'), state[0]
        time.sleep(1)
    else: raise AssertionError('Preparation timeout')
    assert any(s['percent']>=0 and s['screen_off'] and s['wakelock'] for s in samples), 'No measured progress while asleep with preparation lock'
finally:
    (Path(__file__).resolve().parents[1]/'evidence/pacman-background-preparation-v23.json').write_text(json.dumps(samples,ensure_ascii=False,indent=2))
    run('shell','input','keyevent','KEYCODE_WAKEUP')
    run('shell','wm','dismiss-keyguard')
    run('shell','am','start','-n',package+'/io.github.gplaider.tinyagent.AppActivity')

"""Pacman real-UI regression: start swaps button for progress and ready restores it."""
import subprocess, time, re, json
from pathlib import Path
import xml.etree.ElementTree as ET
adb = str(Path.home()/'AppData/Local/Android/Sdk/platform-tools/adb.exe')
def run(*args):
    return subprocess.check_output([adb,'-s','000501423003390',*args],timeout=30)
def ui():
    run('shell','uiautomator','dump','/sdcard/tinyagent-progress.xml')
    return list(ET.fromstring(run('shell','cat','/sdcard/tinyagent-progress.xml')).iter('node'))
def tap(nodes,label):
    n = next(n for n in nodes if n.get('text')==label)
    a,b,c,d = map(int,re.findall(r'\d+',n.get('bounds')))
    run('shell','input','tap',str((a+c)//2),str((b+d)//2))
assert run('shell','getprop','ro.serialno').strip()==b'000501423003390'
tap(ui(),'로컬 백엔드 중단')
time.sleep(2)
tap(ui(),'환경 준비하기')
nodes=ui()
busy=any(n.get('class')=='android.widget.ProgressBar' and n.get('content-desc')=='환경 준비 진행 중' for n in nodes)
assert busy, 'Did not observe the real preparation progress bar'
assert not any(n.get('class')=='android.widget.Button' and n.get('text')=='환경 준비하기' for n in nodes)
for _ in range(20):
    nodes=ui()
    if any(n.get('text')=='환경 준비 완료 · 대화를 시작할 수 있습니다.' for n in nodes): break
    time.sleep(1)
else: raise AssertionError('Ready status not reached')
tap(nodes,'환경 준비하기')
time.sleep(1)
nodes=ui()
assert any(n.get('text')=='환경 준비하기' and n.get('enabled')=='true' for n in nodes), 'Already-running click left progress stuck'
assert not any(n.get('content-desc')=='환경 준비 진행 중' for n in nodes)
report=dict(real_progress_visible=True,button_hidden_while_preparing=True,ready_restores_button=True,already_running_click_recovers=True)
(Path(__file__).resolve().parents[1]/'evidence/pacman-preparation-progress-v21.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))

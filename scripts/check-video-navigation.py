"""Run with the QA video already open. Verify native close/reopen without touching app data."""
import json
from pathlib import Path
import subprocess
import sys
import re
import time

root=Path(__file__).resolve().parents[1]
adb=str(Path.home()/'AppData/Local/Android/Sdk/platform-tools/adb.exe')
serial='100.79.134.53:5555'
def shell(*args):
    return subprocess.check_output([adb,'-s',serial,'shell',*args],text=True,timeout=30)
assert shell('getprop','ro.serialno').strip()=='ZY22J58799'
installed=shell('pm','path','io.github.gplaider.tinyagent.debug').strip().removeprefix('package:')
checksum=shell('sha256sum',installed).split()[0]
expected=sys.argv[1]
assert re.fullmatch('[0-9a-f]{64}',expected) and checksum==expected
def tap(label):
    subprocess.run([str(Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'),'-I','-S','-X','utf8',str(root/'scripts/device-ui.py'),serial,'--tap',label],check=True)
def foreground(activity):
    deadline=time.monotonic()+5
    while True:
        state=shell('dumpsys','activity','activities')
        if any(activity in line for line in state.splitlines() if 'topResumedActivity=' in line):return
        assert time.monotonic()<deadline, activity
        time.sleep(0.2)
rounds=[]
for i in range(3):
    foreground('VideoPreviewActivity')
    tap('닫기')
    foreground('ArtifactActivity')
    rounds.append(dict(round=i+1,closeReturnedToFileMenu=True))
    if i<2:
        tap('재생')
        time.sleep(1)
path=root/'evidence'/('lyriq1-video-navigation-'+checksum[:8]+'.json')
path.write_text(json.dumps(dict(device='ZY22J58799',apk=checksum,rounds=rounds,scope='Three close/reopen transitions; decoded frames/control placement captured separately; rotation/codec matrix not covered'),indent=2)+'\n')
print('PASS: three video close/reopen rounds, file action menu restored')

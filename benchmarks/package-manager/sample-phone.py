"""Sample aggregate app-owned RSS during builds; not a single-command peak measurement."""
import json
from pathlib import Path
import subprocess
import time

adb = str(Path.home()/'AppData/Local/Android/Sdk/platform-tools/adb.exe')
prefix = [adb, '-s', '000501423003390', 'shell']
def read(*argv):
    return subprocess.check_output(prefix+list(argv), timeout=30, text=True, encoding='utf-8')
assert read('getprop', 'ro.serialno').strip() == '000501423003390'
uid = int(read('run-as', 'io.github.gplaider.tinyagent.debug', 'id', '-u'))
assert uid >= 10000
root = Path(__file__).resolve().parents[2]
path = root/'evidence'/f'pacman-build-resources-{int(time.time())}.jsonl'
deadline = time.monotonic()+3600
with path.open('x', encoding='utf-8') as output:
    while time.monotonic() < deadline:
        began = time.monotonic()
        processes = []
        for line in read('ps', '-A', '-o', 'UID,PID,PPID,RSS,NAME').splitlines()[1:]:
            values = line.split(maxsplit=4)
            if len(values) == 5 and values[0] == str(uid):
                processes.append(dict(pid=int(values[1]), ppid=int(values[2]), rss_kib=int(values[3]), name=values[4]))
        battery = dict(line.strip().split(': ', 1) for line in read('dumpsys', 'battery').splitlines() if ': ' in line)
        record = dict(time=time.time(), uid=uid, app_rss_sum_kib=sum(p['rss_kib'] for p in processes),
                      battery_level=battery.get('level'), battery_temperature_tenths_c=battery.get('temperature'),
                      processes=processes, scope='All app-owned processes; sampled RSS sum includes shared pages and concurrent jobs')
        output.write(json.dumps(record)+'\n'); output.flush()
        if int(deadline-time.monotonic()) % 60 < 10:
            print(json.dumps({k:v for k,v in record.items() if k not in ['processes','scope']}), flush=True)
        time.sleep(max(0, 10-(time.monotonic()-began)))
print(path, flush=True)
